###############################################################################
# VeriRAG Backend — Production-Grade Multi-Stage Dockerfile
# AZ-400 Best Practices: non-root user, minimal image, pinned versions
###############################################################################

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Team96 <team96@verirag.dev>" \
      org.opencontainers.image.title="VeriRAG Backend" \
      org.opencontainers.image.description="Django REST API for Cloud-Native RAG" \
      org.opencontainers.image.source="https://github.com/VaibhavKumar2005/cloud-native-ai-library-system"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=rag_backend.settings

# Install only the runtime library (no compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Production: gunicorn; override in docker-compose for dev
CMD ["gunicorn", "rag_backend.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]