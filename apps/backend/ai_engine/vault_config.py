"""
Vault Configuration Module - Secret Retrieval & Key Management
Handles both local (HashiCorp Vault) and cloud (Azure Key Vault) modes.
Provides centralized API key management with caching.
"""

import os
import logging
import hvac
from functools import lru_cache

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
DEPLOY_MODE = os.environ.get('DEPLOY_MODE', 'local').lower()
AZURE_KEY_VAULT_URL = os.environ.get('AZURE_KEY_VAULT_URL')

# Override: if AZURE_KEY_VAULT_URL is set, treat as cloud
if AZURE_KEY_VAULT_URL:
    DEPLOY_MODE = 'cloud'

# ============================================================================
# DUAL-MODE SECRET RETRIEVAL CONFIGURATION
# ============================================================================
# Detects DEPLOY_MODE to choose HashiCorp Vault (local) or Azure Key Vault (cloud).
# API keys are NEVER stored in .env or environment variables.
# ============================================================================
_api_key_cache = {}  # Per-key cache: { "KEY_NAME": { "value": ..., "ts": ... } }
CACHE_TTL = 300  # 5 minutes


def _get_vault_client():
    """
    Creates and validates a HashiCorp Vault client connection (local mode only).
    Returns (client, error_message) tuple.
    """
    vault_url = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
    vault_token = os.environ.get('VAULT_TOKEN')

    if not vault_token:
        return None, "VAULT_TOKEN not set"

    try:
        client = hvac.Client(url=vault_url, token=vault_token)
        if not client.is_authenticated():
            return None, "Vault authentication failed"
        return client, None
    except Exception as e:
        return None, str(e)


def get_api_key_from_vault(key_name="GOOGLE_API_KEY"):
    """
    Retrieves API keys from the active secret backend with per-key caching.

    Dual-mode:
      - DEPLOY_MODE=local  → HashiCorp Vault KV v2 at secret/myapp
      - DEPLOY_MODE=cloud  → Azure Key Vault (via DefaultAzureCredential)

    Falls back to environment variables ONLY if both vault backends fail.

    Expected keys: GOOGLE_API_KEY, GROQ_API_KEY
    
    Args:
        key_name (str): Name of the secret key to retrieve
        
    Returns:
        str: API key value or None if not found
    """
    import time

    current_time = time.time()

    # Check per-key cache first
    cached = _api_key_cache.get(key_name)
    if cached and (current_time - cached["ts"]) < CACHE_TTL:
        return cached["value"]

    api_key = None

    if DEPLOY_MODE == 'cloud' and AZURE_KEY_VAULT_URL:
        # ── Azure Key Vault path ──
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            client = SecretClient(
                vault_url=AZURE_KEY_VAULT_URL,
                credential=DefaultAzureCredential(),
            )
            azure_secret_name = key_name.replace('_', '-')  # GOOGLE_API_KEY → GOOGLE-API-KEY
            api_key = client.get_secret(azure_secret_name).value
            if api_key:
                _api_key_cache[key_name] = {"value": api_key, "ts": current_time}
                logger.info(f"✅ Retrieved {key_name} from Azure Key Vault (cached for {CACHE_TTL}s)")
                return api_key
        except ImportError:
            logger.error("azure-identity or azure-keyvault-secrets not installed")
        except Exception as e:
            logger.error(f"Azure Key Vault error for {key_name}: {e}")
    else:
        # ── HashiCorp Vault path (local mode) ──
        try:
            client, err = _get_vault_client()
            if client is None:
                logger.warning(f"Vault unavailable ({err}), falling back to env for {key_name}")
                return os.environ.get(key_name)

            secret_response = client.secrets.kv.v2.read_secret_version(
                path='myapp',
                mount_point='secret'
            )

            api_key = secret_response['data']['data'].get(key_name)

            if api_key:
                _api_key_cache[key_name] = {"value": api_key, "ts": current_time}
                logger.info(f"✅ Retrieved {key_name} from Vault (cached for {CACHE_TTL}s)")
                return api_key

        except hvac.exceptions.VaultError as ve:
            logger.error(f"Vault API error for {key_name}: {ve}")
        except Exception as e:
            logger.error(f"Vault connection error for {key_name}: {e}")

    logger.warning(f"{key_name} not found in vault, falling back to environment")
    return os.environ.get(key_name)


def get_groq_api_key():
    """
    Retrieves Groq API key from Vault or environment.
    
    Returns:
        str: Groq API key or None if not found
    """
    return get_api_key_from_vault("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")


def get_google_api_key():
    """
    Retrieves Google API key from Vault or environment.
    
    Returns:
        str: Google API key or None if not found
    """
    return get_api_key_from_vault("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
