"""
VeriRAG Test Configuration
Pytest fixtures with mocked Vault, database, and LLM services.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# ── Django Setup ─────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_backend.settings")
os.environ.setdefault("USE_SQLITE_FOR_TESTS", "1")

import django
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from ai_engine.models import Document


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@verirag.dev",
    )


@pytest.fixture
def api_client(user):
    """Return an authenticated DRF APIClient."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


# ============================================================================
# DOCUMENT FIXTURES
# ============================================================================

@pytest.fixture
def sample_document(user, tmp_path):
    """Create a sample Document model instance with a dummy file."""
    dummy_pdf = tmp_path / "test_document.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content for testing")
    doc = Document.objects.create(
        title="Test Research Paper",
        file=dummy_pdf.name,
        user=user,
        processed=False,
    )
    return doc


@pytest.fixture
def processed_document(user, tmp_path):
    """Create a pre-processed document."""
    dummy_pdf = tmp_path / "processed_doc.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 processed content")
    doc = Document.objects.create(
        title="Processed Research Paper",
        file=str(dummy_pdf),
        user=user,
        processed=True,
    )
    return doc


# ============================================================================
# VAULT MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_vault():
    """
    Mock HashiCorp Vault client to avoid real Vault dependency in tests.
    Returns the mock client for assertions.
    """
    with patch.dict("os.environ", {"VAULT_TOKEN": "test-vault-token"}, clear=False), \
         patch("ai_engine.vault_config.hvac.Client") as MockClient:
        instance = MockClient.return_value
        instance.is_authenticated.return_value = True
        instance.sys.is_initialized.return_value = True
        instance.sys.read_seal_status.return_value = {"sealed": False}
        instance.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "GOOGLE_API_KEY": "fake-google-api-key-for-testing",
                    "GROQ_API_KEY": "fake-groq-api-key-for-testing",
                }
            }
        }
        yield instance


@pytest.fixture
def mock_vault_sealed():
    """Mock a sealed Vault instance."""
    with patch("ai_engine.vault_config.hvac.Client") as MockClient:
        instance = MockClient.return_value
        instance.is_authenticated.return_value = True
        instance.sys.is_initialized.return_value = True
        instance.sys.read_seal_status.return_value = {"sealed": True}
        yield instance


@pytest.fixture
def mock_vault_unreachable():
    """Mock an unreachable Vault instance."""
    with patch("ai_engine.vault_config.hvac.Client") as MockClient:
        MockClient.side_effect = Exception("Connection refused")
        yield MockClient


# ============================================================================
# LLM MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_gemini():
    """Mock Azure OpenAI API responses (the actual primary LLM, not Google Gemini)."""
    with patch("ai_engine.rag_logic.call_gemini") as mock_func:
        mock_func.return_value = '{"answer": "Test answer from Azure OpenAI", "faithfulness_score": 0.85}'
        yield mock_func


@pytest.fixture
def mock_gemini_failing():
    """Mock Azure OpenAI API failure (the actual primary LLM)."""
    with patch("ai_engine.rag_logic.call_gemini") as mock_func:
        mock_func.side_effect = Exception("Azure OpenAI quota exceeded")
        yield mock_func


@pytest.fixture
def mock_groq():
    """Mock Groq/Llama-3 API responses."""
    with patch("ai_engine.rag_logic.call_groq_llama") as mock_func:
        mock_func.return_value = '{"answer": "Test answer from Groq", "faithfulness_score": 0.78}'
        yield mock_func


# ============================================================================
# HEALTH CHECK FIXTURES
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis connection for health checks."""
    with patch("ai_engine.views.redis") as mock_redis_mod:
        mock_conn = MagicMock()
        mock_conn.ping.return_value = True
        mock_redis_mod.from_url.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_vault_health():
    """Mock Vault for the health check endpoint specifically."""
    with patch("ai_engine.views.hvac.Client") as MockClient:
        instance = MockClient.return_value
        instance.sys.read_seal_status.return_value = {"sealed": False}
        yield instance
