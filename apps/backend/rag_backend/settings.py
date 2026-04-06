"""
Django settings for VeriRag project.
Production-grade configuration for a Cloud-Native AI Library System.

Security model — Dual-Mode Secret Detection:
  ┌──────────────────────────────────────────────────────────────────┐
  │  DEPLOY_MODE=local  →  HashiCorp Vault (rag-vault container)   │
  │  DEPLOY_MODE=cloud  →  Azure Key Vault (managed identity)      │
  └──────────────────────────────────────────────────────────────────┘

  - API keys (Gemini, Groq) NEVER live in .env or environment vars.
  - In local mode:  hvac reads from Vault KV v2 at secret/myapp.
  - In cloud mode:  azure-identity + azure-keyvault-secrets reads
                    from the Key Vault URL in AZURE_KEY_VAULT_URL.
  - DB credentials use env vars (injected by ACA secrets / K8s
    ExternalSecrets in cloud, or docker-compose .env in local).
"""
import os
import logging
import secrets
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the root .env
load_dotenv(os.path.join(BASE_DIR.parent, '.env'))

# ──────────────────────────────────────────────
# 0. DEPLOY MODE DETECTION
# ──────────────────────────────────────────────
DEPLOY_MODE = os.environ.get('DEPLOY_MODE', 'local').lower()  # "local" | "cloud"
AZURE_KEY_VAULT_URL = os.environ.get('AZURE_KEY_VAULT_URL')

# Override: if AZURE_KEY_VAULT_URL is set, treat as cloud regardless
if AZURE_KEY_VAULT_URL:
    DEPLOY_MODE = 'cloud'

# ──────────────────────────────────────────────
# 0a. VAULT CLIENT — LOCAL MODE (HashiCorp Vault)
# ──────────────────────────────────────────────
VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
VAULT_TOKEN = os.environ.get('VAULT_TOKEN')


def _vault_read(key_name: str) -> str | None:
    """Retrieve a single key from HashiCorp Vault KV v2 at secret/myapp."""
    if DEPLOY_MODE != 'local':
        return None
    try:
        import hvac
        if not VAULT_TOKEN:
            logger.warning("VAULT_TOKEN not set — cannot read secrets from Vault")
            return None
        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if not client.is_authenticated():
            logger.warning("Vault authentication failed")
            return None
        resp = client.secrets.kv.v2.read_secret_version(
            path='myapp', mount_point='secret'
        )
        return resp['data']['data'].get(key_name)
    except Exception as exc:
        logger.warning("Vault read for %s failed: %s", key_name, exc)
        return None


# ──────────────────────────────────────────────
# 0b. VAULT CLIENT — CLOUD MODE (Azure Key Vault)
# ──────────────────────────────────────────────
_azure_kv_client = None

if DEPLOY_MODE == 'cloud' and AZURE_KEY_VAULT_URL:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        _azure_kv_client = SecretClient(
            vault_url=AZURE_KEY_VAULT_URL,
            credential=DefaultAzureCredential(),
        )
        logger.info("Azure Key Vault client initialized: %s", AZURE_KEY_VAULT_URL)
    except ImportError:
        logger.error(
            "azure-identity or azure-keyvault-secrets not installed. "
            "Install with: pip install azure-identity azure-keyvault-secrets"
        )
    except Exception as exc:
        logger.error("Azure Key Vault initialization failed: %s", exc)


def _azure_kv_read(secret_name: str) -> str | None:
    """Retrieve a secret from Azure Key Vault. Names use hyphens (e.g. GOOGLE-API-KEY)."""
    if not _azure_kv_client:
        return None
    try:
        return _azure_kv_client.get_secret(secret_name).value
    except Exception as exc:
        logger.warning("Azure Key Vault read for %s failed: %s", secret_name, exc)
        return None


# ──────────────────────────────────────────────
# 0c. UNIFIED SECRET READER
# ──────────────────────────────────────────────
def get_secret(vault_key: str, azure_key: str | None = None) -> str | None:
    """
    Fetch a secret from the active vault backend.

    Args:
        vault_key:  Key name in HashiCorp Vault KV (e.g. "GOOGLE_API_KEY")
        azure_key:  Key name in Azure Key Vault (e.g. "GOOGLE-API-KEY").
                    Defaults to vault_key with underscores → hyphens.
    """
    if azure_key is None:
        azure_key = vault_key.replace('_', '-')

    if DEPLOY_MODE == 'cloud':
        return _azure_kv_read(azure_key)
    return _vault_read(vault_key)


def env_bool(name: str, default: bool = False) -> bool:
    """Parse common truthy and falsy environment variable values."""
    value = os.environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off', 'release'}:
        return False

    logger.warning("Invalid boolean for %s=%r; using default %s", name, value, default)
    return default


# --- 1. CORE SECURITY ---
DEBUG = env_bool('DEBUG', default=False)
IS_PRODUCTION = DEPLOY_MODE == 'cloud'

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    secrets.token_urlsafe(50) if DEBUG else None
)

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in production.")

env_hosts = os.environ.get('ALLOWED_HOSTS', '').split(',')
default_hosts = ['localhost', '127.0.0.1', '0.0.0.0', 'backend', 'rag-backend']
ALLOWED_HOSTS = list(set(host.strip() for host in env_hosts if host) | set(default_hosts))
if IS_PRODUCTION and not any(host.strip() for host in env_hosts):
    raise ValueError("ALLOWED_HOSTS must be explicitly configured in production.")

# --- 2. APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'django_prometheus',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'csp',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'ai_engine',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'ai_engine.tracing.OpenTelemetryMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'rag_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rag_backend.wsgi.application'

# --- 3. DATABASE (PostgreSQL / PGVector) ---
# In cloud mode, credentials come from ACA secrets / Key Vault.
# In local mode, credentials come from .env via docker-compose.
USE_SQLITE_FOR_TESTS = env_bool('USE_SQLITE_FOR_TESTS', default=False)

if USE_SQLITE_FOR_TESTS:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
else:
    _pg_password = os.environ.get('POSTGRES_PASSWORD') or get_secret('POSTGRES_PASSWORD')
    if not _pg_password and IS_PRODUCTION:
        raise ValueError("POSTGRES_PASSWORD must be set via env var or vault in production.")

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'verirag_db'),
            'USER': os.environ.get('POSTGRES_USER', 'admin'),
            'PASSWORD': _pg_password or 'devpassword',  # fallback only when DEBUG=True
            'HOST': os.environ.get('POSTGRES_HOST', 'rag-db'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

# --- 3a. AZURE AI & SEARCH CONFIGURATION ---
# ────────────────────────────────────────────
# Local mode: Read from environment variables (set via .env or docker-compose)
# Cloud mode: Read from Azure Key Vault using Managed Identity
# Production: NEVER put keys in environment — use Key Vault only

_azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', '').strip()
_azure_openai_key_env = os.environ.get('AZURE_OPENAI_KEY', '').strip()
_azure_search_endpoint = os.environ.get('AZURE_SEARCH_ENDPOINT', '').strip()
_azure_search_key_env = os.environ.get('AZURE_SEARCH_KEY', '').strip()

# In cloud mode, try to fetch from Key Vault (Managed Identity does auth)
if DEPLOY_MODE == 'cloud' and AZURE_KEY_VAULT_URL:
    logger.info("🔐 Loading Azure credentials from Key Vault (Managed Identity)")
    _azure_openai_key = get_secret('AZURE-OPENAI-KEY', 'azure-openai-key')
    _azure_search_key = get_secret('AZURE-SEARCH-KEY', 'azure-search-key')
else:
    # Local mode: use environment variables
    _azure_openai_key = _azure_openai_key_env
    _azure_search_key = _azure_search_key_env

AZURE_OPENAI_ENDPOINT = _azure_openai_endpoint
AZURE_OPENAI_KEY = _azure_openai_key
AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'gpt-4-turbo')

AZURE_SEARCH_ENDPOINT = _azure_search_endpoint
AZURE_SEARCH_KEY = _azure_search_key
AZURE_SEARCH_INDEX = os.environ.get('AZURE_SEARCH_INDEX', 'verirag-documents')

# Validate Azure services configuration
if IS_PRODUCTION:
    missing_azure = []
    if not AZURE_OPENAI_ENDPOINT:
        missing_azure.append('AZURE_OPENAI_ENDPOINT')
    if not AZURE_OPENAI_KEY:
        missing_azure.append('AZURE_OPENAI_KEY (set in Key Vault or env)')
    if not AZURE_SEARCH_ENDPOINT:
        missing_azure.append('AZURE_SEARCH_ENDPOINT')
    if not AZURE_SEARCH_KEY:
        missing_azure.append('AZURE_SEARCH_KEY (set in Key Vault or env)')
    
    if missing_azure:
        raise ValueError(
            f"❌ Azure services not fully configured in production. Missing: {', '.join(missing_azure)}\n"
            f"ℹ️  For local dev: Set AZURE_OPENAI_KEY and AZURE_SEARCH_KEY in .env\n"
            f"ℹ️  For cloud: Set AZURE_KEY_VAULT_URL and add secrets to Azure Key Vault"
        )

logger.info("✅ Azure OpenAI configured: %s (%s)", AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT)
logger.info("✅ Azure AI Search configured: %s", AZURE_SEARCH_ENDPOINT)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')

GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
GOOGLE_OAUTH_SCOPES = [
    scope.strip()
    for scope in os.environ.get('GOOGLE_OAUTH_SCOPES', 'openid email profile').split()
    if scope.strip()
]
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
    'GOOGLE_OAUTH_REDIRECT_URI',
    'http://localhost:8000/api/auth/google/callback/',
).strip()

GITHUB_OAUTH_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID', '').strip()
GITHUB_OAUTH_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', '').strip()
GITHUB_OAUTH_SCOPES = [
    scope.strip()
    for scope in os.environ.get('GITHUB_OAUTH_SCOPES', 'read:user user:email').split()
    if scope.strip()
]
GITHUB_OAUTH_REDIRECT_URI = os.environ.get(
    'GITHUB_OAUTH_REDIRECT_URI',
    'http://localhost:8000/api/auth/github/callback/',
).strip()

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '300/minute',
        'login': '10/minute',
        'query': '30/minute',
        'upload': '20/hour',
        'document_action': '60/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- 5. API DOCUMENTATION (Swagger/OpenAPI) ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'VeriRAG API',
    'DESCRIPTION': 'Azure-powered Cloud-Native RAG System with Hallucination Prevention | Powered by Azure OpenAI + Azure AI Search + Azure PostgreSQL',
    'VERSION': '2.0.0',
    'SCHEMA_PATH_PREFIX': r'/api',
    'AUTHENTICATION_FLOWS': {
        'jwtAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    },
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Local Development (Docker)'},
        {'url': 'https://verirag-backend.azurecontainerapps.io', 'description': 'Azure Container Apps'},
        {'url': 'https://verirag-api.azurewebsites.net', 'description': 'Azure App Service'},
    ],
}

# --- 5. NETWORKING (CORS & CSP) ---
CORS_ALLOW_ALL_ORIGINS = DEBUG

if IS_PRODUCTION:
    CORS_ALLOWED_ORIGINS = [
        host.strip() for host in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if host
    ]
    if not CORS_ALLOWED_ORIGINS:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set in production.")

CSRF_TRUSTED_ORIGINS = [
    host.strip() for host in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if host
]

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'connect-src': ("'self'", 'http://localhost:8000'),
        'script-src': ("'self'",),
        'style-src': ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'),
        'font-src': ("'self'", 'https://fonts.gstatic.com'),
        'img-src': ("'self'", 'data:', 'blob:'),
    }
}

if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# --- 6. STORAGE ---
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 7. CELERY CONFIGURATION ---
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://rag-redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://rag-redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# --- 8. LOGGING ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
