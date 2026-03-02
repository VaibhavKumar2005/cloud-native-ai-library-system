"""
VeriRAG AI Engine Tests
Tests for the core RAG logic, verification pipeline, Vault integration,
LLM failover, and health endpoint.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings

from ai_engine.rag_logic import (
    get_api_key_from_vault,
    verify_faithfulness,
    call_llm_with_fallback,
    _api_key_cache,
    FAITHFULNESS_THRESHOLD,
)
from ai_engine.views import health_check


# ============================================================================
# 1. VAULT INTEGRATION TESTS
# ============================================================================

class TestVaultIntegration:
    """Tests for Vault-based secret retrieval."""

    def test_retrieves_key_from_vault(self, mock_vault):
        """Should retrieve API key from a healthy Vault."""
        # Clear the cache before test
        _api_key_cache.clear()

        key = get_api_key_from_vault("GOOGLE_API_KEY")
        assert key == "fake-google-api-key-for-testing"

    def test_caches_vault_key(self, mock_vault):
        """Should cache Vault keys and not re-query within TTL."""
        _api_key_cache.clear()

        # First call — hits Vault
        key1 = get_api_key_from_vault("GOOGLE_API_KEY")
        # Second call — should use cache
        key2 = get_api_key_from_vault("GOOGLE_API_KEY")

        assert key1 == key2 == "fake-google-api-key-for-testing"
        # Vault should only be called once due to caching
        assert mock_vault.secrets.kv.v2.read_secret_version.call_count == 1

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "env-fallback-key"}, clear=False)
    def test_falls_back_to_env_when_vault_unreachable(self, mock_vault_unreachable):
        """Should fall back to environment variable when Vault is down."""
        _api_key_cache.clear()
        key = get_api_key_from_vault("GOOGLE_API_KEY")
        assert key == "env-fallback-key"

    @patch.dict("os.environ", {"VAULT_TOKEN": ""}, clear=False)
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "env-no-token-key"}, clear=False)
    def test_falls_back_when_no_vault_token(self):
        """Should fall back to env var when VAULT_TOKEN is not set."""
        _api_key_cache.clear()
        key = get_api_key_from_vault("GOOGLE_API_KEY")
        assert key == "env-no-token-key"

    def test_retrieves_groq_key(self, mock_vault):
        """Should retrieve Groq API key from Vault."""
        _api_key_cache.clear()
        key = get_api_key_from_vault("GROQ_API_KEY")
        assert key == "fake-groq-api-key-for-testing"


# ============================================================================
# 2. FAITHFULNESS VERIFICATION TESTS
# ============================================================================

class TestVerifyFaithfulness:
    """Tests for the verify_faithfulness heuristic checker."""

    def test_high_overlap_gives_high_score(self):
        """High term overlap between answer and context should yield high score."""
        context = "The population of France is approximately 67 million people."
        answer = "The population of France is about 67 million."
        query = "What is the population of France?"

        score, explanation = verify_faithfulness(answer, context, query)
        assert score >= 0.6, f"Expected high score, got {score}"

    def test_hallucinated_answer_gives_low_score(self):
        """Answer with many new terms not in context should be penalized."""
        context = "The Eiffel Tower is located in Paris and was built in 1889."
        answer = "The Eiffel Tower was originally constructed as a telecommunication satellite base for quantum computing research."
        query = "What is the Eiffel Tower?"

        score, explanation = verify_faithfulness(answer, context, query)
        assert score < 0.8, f"Expected lower score for hallucinated answer, got {score}"

    def test_empty_answer_returns_midrange(self):
        """Empty answer should return a midrange score."""
        context = "Some context text with information."
        answer = ""
        query = "What?"

        score, explanation = verify_faithfulness(answer, context, query)
        assert 0.3 <= score <= 0.8, f"Expected midrange, got {score}"

    def test_identical_text_gives_max_score(self):
        """Answer that is nearly identical to context should score high."""
        text = "Machine learning is a subset of artificial intelligence that enables systems to learn from data."
        score, explanation = verify_faithfulness(text, text, "What is ML?")
        assert score >= 0.8, f"Expected high score for identical text, got {score}"

    def test_returns_explanation_string(self):
        """Should always return a string explanation."""
        score, explanation = verify_faithfulness("test answer", "test context", "q")
        assert isinstance(explanation, str)
        assert len(explanation) > 0


# ============================================================================
# 3. LLM FAILOVER TESTS
# ============================================================================

class TestLLMFailover:
    """Tests for the dual-LLM failover mechanism."""

    def test_gemini_primary_success(self, mock_vault, mock_gemini):
        """Should use Gemini as primary and return its response."""
        response, model = call_llm_with_fallback("test prompt", "fake-api-key")
        assert model == "gemini"
        parsed = json.loads(response)
        assert "answer" in parsed

    def test_failover_to_groq_on_gemini_failure(self, mock_vault, mock_gemini_failing, mock_groq):
        """Should failover to Groq when Gemini fails."""
        response, model = call_llm_with_fallback("test prompt", "fake-api-key")
        assert model == "groq"
        parsed = json.loads(response)
        assert "answer" in parsed

    def test_both_llms_fail_returns_error(self, mock_vault, mock_gemini_failing):
        """Should return error JSON when both LLMs fail."""
        with patch("ai_engine.rag_logic.call_groq_llama", side_effect=Exception("Groq down")):
            response, model = call_llm_with_fallback("test prompt", "fake-api-key")
            assert model == "error"
            parsed = json.loads(response)
            assert parsed["verification_passed"] is False


# ============================================================================
# 4. HEALTH ENDPOINT TESTS
# ============================================================================

@pytest.mark.django_db
class TestHealthEndpoint:
    """Tests for the GET /api/health/ public endpoint."""

    def test_health_returns_200_when_all_healthy(self, anon_client, mock_redis, mock_vault_health):
        """Health endpoint should return 200 when all services are up."""
        response = anon_client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert "postgresql" in data["services"]
        assert "redis" in data["services"]
        assert "vault" in data["services"]

    def test_health_returns_503_when_redis_down(self, anon_client, mock_vault_health):
        """Health should return 503 when Redis is unreachable."""
        with patch("ai_engine.views.redis") as mock_redis_mod:
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = Exception("Connection refused")
            mock_redis_mod.from_url.return_value = mock_conn

            response = anon_client.get("/api/health/")
            assert response.status_code == 503
            data = response.json()
            assert data["healthy"] is False
            assert data["services"]["redis"]["status"] == "unhealthy"

    def test_health_no_auth_required(self, anon_client, mock_redis, mock_vault_health):
        """Health endpoint must be accessible without authentication."""
        response = anon_client.get("/api/health/")
        assert response.status_code in (200, 503)  # either is fine, just not 401/403

    def test_health_reports_latency(self, anon_client, mock_redis, mock_vault_health):
        """Each service check should report latency_ms."""
        response = anon_client.get("/api/health/")
        data = response.json()
        for service in data["services"].values():
            assert "latency_ms" in service
            assert isinstance(service["latency_ms"], (int, float))


# ============================================================================
# 5. DOCUMENT API TESTS
# ============================================================================

@pytest.mark.django_db
class TestDocumentAPI:
    """Tests for the document CRUD endpoints."""

    def test_list_documents_empty(self, api_client):
        """Should return empty list when no documents uploaded."""
        response = api_client.get("/api/documents/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_documents_authenticated_only(self, anon_client):
        """Should reject unauthenticated requests."""
        response = anon_client.get("/api/documents/")
        assert response.status_code == 401

    def test_document_isolation(self, api_client, processed_document, db):
        """User should only see their own documents."""
        from django.contrib.auth.models import User
        other_user = User.objects.create_user("other", password="pass")
        from ai_engine.models import Document
        Document.objects.create(title="Other Doc", user=other_user, processed=True)

        response = api_client.get("/api/documents/")
        titles = [d["title"] for d in response.json()]
        assert "Other Doc" not in titles


# ============================================================================
# 6. QUERY ENDPOINT TESTS
# ============================================================================

@pytest.mark.django_db
class TestQueryEndpoint:
    """Tests for POST /api/query/."""

    def test_query_requires_auth(self, anon_client):
        """Should reject unauthenticated queries."""
        response = anon_client.post("/api/query/", {"query": "hello"})
        assert response.status_code == 401

    def test_query_requires_body(self, api_client):
        """Should return 400 when no query body is provided."""
        response = api_client.post("/api/query/", {})
        assert response.status_code == 400

    def test_query_rejects_long_input(self, api_client):
        """Should reject queries longer than 2000 characters."""
        response = api_client.post("/api/query/", {"query": "x" * 2001})
        assert response.status_code == 400

    def test_query_returns_standardized_response(self, api_client):
        """Response should contain all VeriRAG fields."""
        with patch("ai_engine.views.get_verified_answer") as mock_answer:
            mock_answer.return_value = {
                "answer": "Test",
                "faithfulness_score": 0.9,
                "explanation": "Good",
                "source_citation": "Page 1",
                "verification_passed": True,
                "model_used": "gemini",
                "context_chunks_used": 3,
            }
            response = api_client.post("/api/query/", {"query": "What is AI?"})
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "faithfulness_score" in data
            assert "verification_passed" in data
            assert "model_used" in data
