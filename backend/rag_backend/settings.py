"""
Django settings for VeriRag project.
Production-grade configuration for a Cloud-Native AI Library System.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the root .env
load_dotenv(os.path.join(BASE_DIR.parent, '.env'))

# --- 1. CORE SECURITY ---
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Secure Secret Key handling
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    secrets.token_urlsafe(50) if DEBUG else None
)

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in production via Environment Variables")

# Parse ALLOWED_HOSTS and ensure internal Docker networking is always trusted
env_hosts = os.environ.get('ALLOWED_HOSTS', '').split(',')
default_hosts = ['localhost', '127.0.0.1', '0.0.0.0', 'backend'] # 'backend' is the Docker service name
ALLOWED_HOSTS = list(set(host.strip() for host in env_hosts if host) | set(default_hosts))

# --- 2. APPLICATION DEFINITION ---
INSTALLED_APPS = [
    # Monitoring & Observability
    'django_prometheus',
    
    # Core Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third Party Tools
    'corsheaders',
    'csp',                # <--- KEEP THIS
    # 'django-csp',       # <--- DELETE OR COMMENT THIS OUT
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    
    # Internal AI Engine
    'ai_engine',
]

MIDDLEWARE = [
    # Prometheus Metrics (Must wrap other middleware)
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # Content Security Policy
    'csp.middleware.CSPMiddleware',
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Prometheus Metrics (End wrap)
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'rag_backend.urls'

# --- 3. DATABASE (PostgreSQL / PGVector) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'library_db'),
        'USER': os.environ.get('POSTGRES_USER', 'admin'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'devpassword'),
        'HOST': os.environ.get('POSTGRES_HOST', 'postgres'), # Match Docker service name
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
    CORS_ALLOWED_ORIGINS = os.environ.get(
        'CORS_ALLOWED_ORIGINS', 
        'http://localhost:5173'
    ).split(',')

# Content Security Policy (v4.0+ format)
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
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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

# --- 7. CELERY CONFIGURATION (Background Task Processing) ---
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task routing for specialized queues
CELERY_TASK_ROUTES = {
    'ai_engine.tasks.ingest_document_task': {'queue': 'ingestion'},
    'ai_engine.tasks.process_pending_documents': {'queue': 'ingestion'},
    'ai_engine.tasks.system_health_check': {'queue': 'monitoring'},
    'ai_engine.tasks.cleanup_orphaned_vectors': {'queue': 'maintenance'},
}

# --- 8. OPENTELEMETRY CONFIGURATION ---
OTEL_ENABLED = os.environ.get('OTEL_ENABLED', 'true').lower() == 'true'
OTEL_SERVICE_NAME = os.environ.get('OTEL_SERVICE_NAME', 'verirag-backend')
OTEL_EXPORTER_ENDPOINT = os.environ.get('OTEL_EXPORTER_ENDPOINT', 'http://jaeger:4317')

# --- 9. LOGGING CONFIGURATION ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'ai_engine': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}