"""
VeriRAG AI Engine Tests
Tests for the core RAG logic, verification pipeline, Vault integration,
LLM failover, and health endpoint.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_engine.rag_logic import (
    get_api_key_from_vault,
    verify_faithfulness,
    call_llm_with_fallback,
    _api_key_cache,
    FAITHFULNESS_THRESHOLD,
)
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

    def test_accepts_request_context_without_affecting_failover(self, mock_vault, mock_gemini):
        """Pipeline should accept optional tracing context metadata."""
        with patch("ai_engine.rag_logic.PGVector") as mock_pgvector, \
             patch("ai_engine.rag_logic.get_embedding_model"), \
             patch("ai_engine.rag_logic.get_api_key_from_vault", return_value="fake-api-key"):
            doc = MagicMock()
            doc.page_content = "France has a population of approximately 67 million people."
            doc.metadata = {
                "page": 1,
                "document_title": "Population Report",
                "document_id": "doc-1",
            }
            mock_pgvector.return_value.similarity_search.return_value = [doc]

            from ai_engine.rag_logic import get_verified_answer

            result = get_verified_answer(
                "What is the population of France?",
                user_id=1,
                request_context={"query_id": "q-123", "trace_id": "abc123"},
            )

            assert result["model_used"] == "gemini"
            assert result["context_chunks_used"] == 1


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
        assert "services" not in data

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

    def test_health_no_auth_required(self, anon_client, mock_redis, mock_vault_health):
        """Health endpoint must be accessible without authentication."""
        response = anon_client.get("/api/health/")
        assert response.status_code in (200, 503)  # either is fine, just not 401/403

    def test_health_details_requires_auth(self, anon_client):
        response = anon_client.get("/api/health/details/")
        assert response.status_code == 401

    def test_health_details_reports_service_latency(self, api_client, mock_redis, mock_vault_health):
        """Detailed health endpoint should include per-service latency for authenticated users."""
        response = api_client.get("/api/health/details/")
        data = response.json()
        for service in data["services"].values():
            assert "latency_ms" in service
            assert isinstance(service["latency_ms"], (int, float))


@pytest.mark.django_db
class TestQueryTracingMetadata:
    """Tracing metadata should be returned from the query endpoint."""

    @patch("ai_engine.views.get_trace_id", return_value="trace-123")
    @patch("ai_engine.views.get_verified_answer")
    def test_query_response_includes_trace_headers(self, mock_get_verified_answer, mock_trace_id, api_client):
        mock_get_verified_answer.return_value = {
            "answer": "Test answer",
            "faithfulness_score": 0.9,
            "explanation": "Found in context",
            "source_citation": "Page 1",
            "evidence_items": [],
            "verification_passed": True,
            "model_used": "gemini",
            "context_chunks_used": 1,
        }

        response = api_client.post(
            "/api/query/",
            {"query": "test question"},
            format="json",
            HTTP_X_REQUEST_ID="req-123",
        )

        assert response.status_code == 200
        assert response["X-Trace-Id"] == "trace-123"
        assert response["X-Query-Id"] == "req-123"
        payload = response.json()
        assert payload["trace_id"] == "trace-123"
        assert payload["query_id"] == "req-123"
        assert "latency_ms" in payload
        mock_get_verified_answer.assert_called_once()


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

    @patch("ai_engine.views.ingest_document_task.delay")
    def test_upload_document_accepts_multipart_pdf(self, mock_delay, api_client):
        """Authenticated users should be able to upload PDFs as multipart form data."""
        pdf = SimpleUploadedFile(
            "sample.pdf",
            b"%PDF-1.4 test document",
            content_type="application/pdf",
        )

        response = api_client.post(
            "/api/documents/",
            {"title": "Sample PDF", "file": pdf},
            format="multipart",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Sample PDF"
        assert data["processed"] is False
        mock_delay.assert_called_once()

    @patch("ai_engine.views.ingest_document_task.delay", side_effect=Exception("broker down"))
    def test_upload_document_still_succeeds_when_queue_unavailable(self, mock_delay, api_client):
        """Uploads should not fail just because Redis/Celery is temporarily unavailable."""
        pdf = SimpleUploadedFile(
            "queue-failure.pdf",
            b"%PDF-1.4 queue failure",
            content_type="application/pdf",
        )

        response = api_client.post(
            "/api/documents/",
            {"title": "Queue Failure PDF", "file": pdf},
            format="multipart",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Queue Failure PDF"
        assert data["processed"] is False
        mock_delay.assert_called_once()

    def test_upload_rejects_non_pdf_payload(self, api_client):
        not_pdf = SimpleUploadedFile(
            "bad.txt",
            b"plain text payload",
            content_type="text/plain",
        )

        response = api_client.post(
            "/api/documents/",
            {"title": "Not PDF", "file": not_pdf},
            format="multipart",
        )

        assert response.status_code == 400
        assert "file" in response.json()


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
                "evidence_items": [
                    {
                        "source_index": 1,
                        "document_title": "Test Document",
                        "page": 1,
                        "chunk_index": 0,
                        "citation": "Test Document (Page 1)",
                        "excerpt": "Relevant excerpt",
                    }
                ],
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
            assert "evidence_items" in data
