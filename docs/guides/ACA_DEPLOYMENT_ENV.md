# ACA Deployment Environment Variables Guide

This guide defines the environment variables required to deploy VeriRAG Backend to Azure Container Apps (ACA).

## Overview

VeriRAG uses a **dual-mode secret management system**:
- **Local/Dev**: HashiCorp Vault (running in docker-compose)
- **Cloud (ACA)**: Azure Key Vault (managed identity authentication)

## Environment Variable Categories

### 1. Core Django Configuration

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DJANGO_SECRET_KEY` | Yes | `randomsecurestring...` | Must be generated securely. Use 50+ chars. |
| `DEBUG` | Yes | `False` | Set to `False` in production (ACA). |
| `DEPLOY_MODE` | Yes | `cloud` | Set to `cloud` for ACA deployment. |
| `ALLOWED_HOSTS` | Yes | `myapi.aca.azurecontainerapps.io,api.verirag.com` | Comma-separated list of allowed domains. |
| `FRONTEND_URL` | Yes | `https://myapp.aca.azurecontainerapps.io` | Frontend domain for OAuth redirects. |

**Example for ACA:**
```bash
DJANGO_SECRET_KEY=your-secure-random-key-50-chars-min
DEBUG=False
DEPLOY_MODE=cloud
ALLOWED_HOSTS=verirag-api.aca.azurecontainerapps.io,*.azurecontainerapps.io
FRONTEND_URL=https://verirag-frontend.aca.azurecontainerapps.io
```

---

### 2. Database (PostgreSQL + pgvector)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `POSTGRES_USER` | Yes | `admin` | Database user |
| `POSTGRES_PASSWORD` | Yes | — | Secure password (store in Key Vault) |
| `POSTGRES_DB` | Yes | `verirag_db` | Database name |
| `POSTGRES_HOST` | Yes | — | ACA: Azure Database for PostgreSQL hostname |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |

**ACA Setup:**
```bash
POSTGRES_HOST=verirag-db-server.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_USER=adminuser@verirag-db-server
POSTGRES_PASSWORD=SecurePassword123!
POSTGRES_DB=verirag_db
```

---

### 3. Cache & Task Queue (Redis)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `REDIS_URL` | Yes | `redis://rag-redis:6379/0` | Full Redis connection URL |
| `CELERY_BROKER_URL` | No | Uses REDIS_URL | Celery broker (defaults to REDIS_URL) |
| `CELERY_RESULT_BACKEND` | No | Uses REDIS_URL | Celery results backend (defaults to REDIS_URL) |

**ACA Setup (Azure Cache for Redis):**
```bash
REDIS_URL=redis://:EncodedPassword@verirag-cache.redis.cache.windows.net:6379/0?ssl=True
```

---

### 4. Azure Key Vault (Secrets Management)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `AZURE_KEY_VAULT_URL` | Yes | — | Full Key Vault URL |
| `AZURE_KEY_VAULT_TENANT_ID` | No | — | Auto-detected by DefaultAzureCredential |

**ACA Setup:**
```bash
AZURE_KEY_VAULT_URL=https://verirag-kv.vault.azure.net/
# Tenant ID is auto-detected via Managed Identity
```

**Secrets to store in Key Vault:**
- `azure-openai-key` → AZURE_OPENAI_KEY
- `azure-search-key` → AZURE_SEARCH_KEY
- `gemini-api-key` → (if using Google Gemini)
- `groq-api-key` → (if using Groq)

---

### 5. Azure OpenAI

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI service endpoint |
| `AZURE_OPENAI_KEY` | Yes | — | API key (from Key Vault in cloud) |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | `gpt-4-turbo` | Azure deployment name |

**ACA Setup:**
```bash
AZURE_OPENAI_ENDPOINT=https://verirag-openai.openai.azure.com/
AZURE_OPENAI_KEY=<stored-in-key-vault>
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo-20240409
```

---

### 6. Azure AI Search

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `AZURE_SEARCH_ENDPOINT` | Yes | — | Azure AI Search service endpoint |
| `AZURE_SEARCH_KEY` | Yes | — | API key (from Key Vault in cloud) |
| `AZURE_SEARCH_INDEX` | Yes | `verirag-documents` | Search index name |

**ACA Setup:**
```bash
AZURE_SEARCH_ENDPOINT=https://verirag-search.search.windows.net/
AZURE_SEARCH_KEY=<stored-in-key-vault>
AZURE_SEARCH_INDEX=verirag-documents
```

---

### 7. Google OAuth Authentication

| Variable | Required | Sensitive | Notes |
|----------|----------|-----------|-------|
| `GOOGLE_OAUTH_CLIENT_ID` | No | No | From Google Cloud Console |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | Yes | Store in Key Vault |
| `GOOGLE_OAUTH_REDIRECT_URI` | No | No | Match Google Console config |
| `GOOGLE_OAUTH_SCOPES` | No | No | Default: `openid email profile` |

**ACA Setup:**
```bash
GOOGLE_OAUTH_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<stored-in-key-vault>
GOOGLE_OAUTH_REDIRECT_URI=https://verirag-api.aca.azurecontainerapps.io/api/auth/google/callback/
GOOGLE_OAUTH_SCOPES=openid email profile
```

---

### 8. GitHub OAuth Authentication

| Variable | Required | Sensitive | Notes |
|----------|----------|-----------|-------|
| `GITHUB_OAUTH_CLIENT_ID` | No | No | From GitHub Settings → OAuth Apps |
| `GITHUB_OAUTH_CLIENT_SECRET` | No | Yes | Store in Key Vault |
| `GITHUB_OAUTH_REDIRECT_URI` | No | No | Match GitHub settings |
| `GITHUB_OAUTH_SCOPES` | No | No | Default: `read:user user:email` |

**ACA Setup:**
```bash
GITHUB_OAUTH_CLIENT_ID=Iv1.xxxxxxxxxxxxx
GITHUB_OAUTH_CLIENT_SECRET=<stored-in-key-vault>
GITHUB_OAUTH_REDIRECT_URI=https://verirag-api.aca.azurecontainerapps.io/api/auth/github/callback/
GITHUB_OAUTH_SCOPES=read:user user:email
```

---

### 9. Security & CORS Configuration

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `CORS_ALLOWED_ORIGINS` | Yes | — | Comma-separated list of allowed origins |
| `CSRF_TRUSTED_ORIGINS` | Yes | — | Comma-separated list for CSRF checks |
| `SECURE_SSL_REDIRECT` | Yes | `True` | Force HTTPS (always True in ACA) |
| `SESSION_COOKIE_SECURE` | Yes | `True` | Only send cookies over HTTPS |
| `CSRF_COOKIE_SECURE` | Yes | `True` | Only send CSRF cookie over HTTPS |

**ACA Setup:**
```bash
CORS_ALLOWED_ORIGINS=https://verirag-frontend.aca.azurecontainerapps.io,https://app.verirag.com
CSRF_TRUSTED_ORIGINS=https://verirag-frontend.aca.azurecontainerapps.io,https://app.verirag.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

### 10. Observability & Monitoring

| Variable | Optional | Default | Notes |
|----------|----------|---------|-------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry endpoint (e.g., Application Insights) |
| `OTEL_SERVICE_NAME` | No | `verirag-backend` | Service name for traces |
| `OTEL_EXPORTER_OTLP_HEADERS` | No | — | Headers for telemetry (auth tokens) |

---

## Complete ACA Environment Variables Example

```bash
# Core Django
DJANGO_SECRET_KEY=abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx
DEBUG=False
DEPLOY_MODE=cloud
ALLOWED_HOSTS=verirag-api.aca.azurecontainerapps.io
FRONTEND_URL=https://verirag-frontend.aca.azurecontainerapps.io

# Database
POSTGRES_HOST=verirag-db-server.postgres.database.azure.com
POSTGRES_USER=adminuser@verirag-db-server
POSTGRES_PASSWORD=SecurePassword123!
POSTGRES_DB=verirag_db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://:EncodedPassword@verirag-cache.redis.cache.windows.net:6379/0?ssl=True

# Azure Key Vault (Managed Identity Authentication)
AZURE_KEY_VAULT_URL=https://verirag-kv.vault.azure.net/

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://verirag-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo-20240409

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://verirag-search.search.windows.net/
AZURE_SEARCH_INDEX=verirag-documents

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_REDIRECT_URI=https://verirag-api.aca.azurecontainerapps.io/api/auth/google/callback/

# GitHub OAuth
GITHUB_OAUTH_CLIENT_ID=Iv1.xxxxxxxxxxxxx
GITHUB_OAUTH_REDIRECT_URI=https://verirag-api.aca.azurecontainerapps.io/api/auth/github/callback/

# Security
CORS_ALLOWED_ORIGINS=https://verirag-frontend.aca.azurecontainerapps.io
CSRF_TRUSTED_ORIGINS=https://verirag-frontend.aca.azurecontainerapps.io
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## How to Set Environment Variables in ACA

### Option 1: Azure CLI

```bash
az containerapp update \
  --name verirag-backend \
  --resource-group myResourceGroup \
  --set-env-vars \
    DJANGO_SECRET_KEY="abcd1234..." \
    DEBUG="False" \
    POSTGRES_HOST="..." \
    # ... more vars
```

### Option 2: Azure Container Apps Portal

1. Go to **Azure Container Apps** → Select **verirag-backend**
2. Click **Edit and deploy**
3. Go to **Containers** tab
4. Under **Environment variables**, add each variable

### Option 3: Infrastructure as Code (Bicep)

Define in `main.bicep`:
```bicep
env: [
  {
    name: 'DJANGO_SECRET_KEY'
    secretRef: 'django-secret-key'
  }
  {
    name: 'DEBUG'
    value: 'False'
  }
  // ... more vars
]
secrets: [
  {
    name: 'django-secret-key'
    value: keyVault.getSecret('django-secret-key')
  }
]
```

---

## Health Check Endpoint

VeriRAG provides two health check endpoints:

### Public Health Check (for ACA liveness probes)
```
GET /api/health/
Response: { "healthy": true, "timestamp": "...", "version": "2.0.0" }
Status: 200 OK if healthy, 503 SERVICE UNAVAILABLE if unhealthy
```

### Authenticated Detailed Health Check (for monitoring)
```
GET /api/health/details/
Headers: Authorization: Bearer {JWT_TOKEN}
Response: {
  "status": "ok|degraded|critical",
  "healthy": true,
  "timestamp": "...",
  "version": "2.0.0",
  "deployment_mode": "cloud",
  "components": {
    "postgres": { "status": "healthy", "latency_ms": 2, "component": "PostgreSQL + pgvector" },
    "redis": { "status": "healthy", "latency_ms": 1, "component": "Redis (Celery broker & cache)" },
    "azure_keyvault": { "status": "healthy", "latency_ms": 50, "component": "Azure Key Vault" },
    "azure_openai": { "status": "healthy", "latency_ms": 150, "component": "Azure OpenAI" }
  }
}
```

---

## Graceful Shutdown

VeriRAG is configured for graceful shutdown in ACA:
- **Signal**: SIGTERM (ACA sends 30s before forced termination)
- **Behavior**: Closes DB connections, drains Celery queue, exits cleanly
- **Gunicorn config**: 30s graceful timeout, 60s request timeout

---

## Security Best Practices

1. **Never commit `.env` files** - Use Key Vault for all secrets
2. **Rotate secrets regularly** - Update OAuth credentials every 90 days
3. **Use Managed Identity** - ACA automatically authenticates with Key Vault
4. **HTTPS only** - All traffic to/from ACA is encrypted
5. **Rate limiting** - API is throttled to prevent abuse
6. **CORS validation** - Only frontend domain can make browser requests

---

## Troubleshooting

### 503 Service Unavailable
Check `/api/health/details/` to identify which component is down:
```bash
curl -H "Authorization: Bearer $TOKEN" https://verirag-api.aca.azurecontainerapps.io/api/health/details/
```

### Database Connection Issues
Ensure:
- `POSTGRES_HOST` is accessible from ACA (firewall rules)
- `POSTGRES_USER` format is `username@servername` for Azure PostgreSQL
- `POSTGRES_PASSWORD` contains special characters encoded properly

### Secrets Not Loading
- Verify `AZURE_KEY_VAULT_URL` is correct
- Ensure ACA system-assigned identity has "Get Secret" permission on Key Vault
- Check Key Vault secret names use hyphens (e.g., `azure-openai-key`)

---

For more details, see:
- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Django Settings Reference](./docs/guides/DEPLOYMENT.md)
- [VeriRAG Architecture Guide](./docs/showcase/ARCHITECTURE.md)
