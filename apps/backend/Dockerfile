###############################################################################
# VeriRAG Backend — Production-Grade Multi-Stage Dockerfile for ACA
# Best Practices: non-root user, minimal image, ACA-optimized runtime
###############################################################################

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Security: Upgrade all OS packages to latest patched versions, install build deps
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install --ignore-installed -r requirements.txt && \
    find /install -type f -name '*.pyc' -delete && \
    find /install -type d -name '__pycache__' -delete

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Team96 <team96@verirag.dev>" \
      org.opencontainers.image.title="VeriRAG Backend" \
      org.opencontainers.image.description="Django REST API for Cloud-Native RAG" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.source="https://github.com/VaibhavKumar2005/cloud-native-ai-library-system"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=rag_backend.settings

# Security: Upgrade all OS packages to latest patched versions with Python 3.12 (more patches)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user (AZ-400 requirement)
RUN groupadd -r verirag && useradd -r -g verirag -d /app -s /sbin/nologin verirag

WORKDIR /app

# Copy application code
COPY --chown=verirag:verirag . .

# Create required directories
RUN mkdir -p /app/media/pdfs /app/staticfiles \
    && chown -R verirag:verirag /app

# Switch to non-root user
USER verirag

EXPOSE 8000

# ACA-optimized health check (30s timeout for ACA graceful shutdown window)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Graceful shutdown signal (tells ACA to use SIGTERM)
STOPSIGNAL SIGTERM

# Production: gunicorn with ACA-optimized settings
# - workers: 3 (adjust based on ACA CPU allocation)
# - graceful-timeout: 30s (ACA sends SIGTERM before this)
# - timeout: 60s (individual request max time)
# - max-requests: 1000 (prevent memory leaks)
# - keep-alive: 65 (connection persistence)
CMD ["gunicorn", "rag_backend.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--graceful-timeout", "30", \
     "--timeout", "60", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--keep-alive", "65", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
