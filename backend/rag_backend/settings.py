"""
Django settings for VeriRag project.
Production-grade configuration for a Cloud-Native AI Library System.

Security model:
  - API keys (Gemini, Groq) live in HashiCorp Vault at secret/myapp.
  - .env only carries VAULT_ADDR + VAULT_TOKEN — never raw API keys.
  - DB credentials use env vars in dev; in production, Vault or Azure Key Vault.
"""
import os
import logging
import secrets
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the root .env
load_dotenv(os.path.join(BASE_DIR.parent, '.env'))

# --- 0. VAULT BOOTSTRAP (run before anything that might need secrets) ---
VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
VAULT_TOKEN = os.environ.get('VAULT_TOKEN')


def _vault_read(key_name: str) -> str | None:
    """Retrieve a single key from Vault KV v2 at secret/myapp."""
    try:
        import hvac
        if not VAULT_TOKEN:
            return None
        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if not client.is_authenticated():
            return None
        resp = client.secrets.kv.v2.read_secret_version(
            path='myapp', mount_point='secret'
        )
        return resp['data']['data'].get(key_name)
    except Exception as exc:
        logger.warning("Vault read for %s failed: %s", key_name, exc)
        return None

# --- 1. CORE SECURITY ---
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    secrets.token_urlsafe(50) if DEBUG else None
)

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in production.")

env_hosts = os.environ.get('ALLOWED_HOSTS', '').split(',')
default_hosts = ['localhost', '127.0.0.1', '0.0.0.0', 'backend', 'rag-backend']
ALLOWED_HOSTS = list(set(host.strip() for host in env_hosts if host) | set(default_hosts))

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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'verirag_db'),
        'USER': os.environ.get('POSTGRES_USER', 'admin'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'devpassword'),
        'HOST': os.environ.get('POSTGRES_HOST', 'rag-db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# --- 4. API & AUTHENTICATION (JWT) ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- 5. NETWORKING (CORS & CSP) ---
CORS_ALLOW_ALL_ORIGINS = DEBUG

if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        host.strip() for host in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if host
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