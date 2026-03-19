# Azure Container Apps (ACA) Deployment Guide

## Overview

VeriRAG is now fully optimized for Azure Container Apps deployment. This guide covers environment configuration, deployment steps, and monitoring.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React Frontend)                                   │
│  📱 Deployed: Static Site (Azure Blob + CDN)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Azure Container Apps (VeriRAG Backend)                      │
│  💻 Django REST API on Port 8000                            │
│  ✅ Multi-container support (future: sidecars)              │
└──┬────────────────┬──────────────────┬──────────────────────┘
   │                │                  │
   ▼                ▼                  ▼
┌─────────────┐ ┌──────────────┐ ┌─────────────────┐
│ PostgreSQL  │ │   Redis      │ │ Azure OpenAI    │
│ (pgvector)  │ │ (Celery)     │ │ (AI/RAG)        │
└─────────────┘ └──────────────┘ └─────────────────┘
   ▼ (managed)      ▼ (managed)      ▼ (Azure service)
Azure Database   Azure Cache      Azure OpenAI
```

## Environment Variables (Required)

### Core Django Settings

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here (generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_SETTINGS_MODULE=rag_backend.settings
DEBUG=False  # NEVER True in production

# Deployment Mode
DEPLOY_MODE=cloud
ENVIRONMENT=production  # or staging, development
```

### Database (Azure Database for PostgreSQL)

```bash
# PostgreSQL Connection
DATABASE_ENGINE=django.contrib.postgresql
DATABASE_NAME=verirag_db
DATABASE_USER=verirag_user
DATABASE_PASSWORD=<strong-password>
DATABASE_HOST=verirag.postgres.database.azure.com
DATABASE_PORT=5432
DATABASE_ATOMIC_REQUESTS=False

# pgvector Extension (must be enabled in Azure)
# Enable in Azure Portal: Server Parameters → azure.extensions → pgvector ON
```

### Redis (Azure Cache for Redis)

```bash
# Redis/Celery Configuration
REDIS_URL=redis://:password@verirag.redis.cache.windows.net:6379/0?ssl=True
# For Azure Cache for Redis: URL format is redis://:password@hostname:port/db?ssl=True

# Celery Settings
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
CELERY_TASK_SERIALIZER=json
CELERY_ACCEPT_CONTENT=json
CELERY_RESULT_SERIALIZER=json
```

### Azure OpenAI (LLM)

```bash
# Azure OpenAI API Configuration
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Deployment Model Names (from Azure OpenAI Studio)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-turbo  # or gpt-35-turbo
AZURE_AI_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_AI_SEARCH_KEY=<search-key>
```

### Azure Key Vault (Secrets Management)

```bash
# Azure Key Vault for Secrets
AZURE_KEY_VAULT_URL=https://<vault-name>.vault.azure.nzt/
AZURE_KEY_VAULT_TENANT_ID=<tenant-id>
AZURE_KEY_VAULT_CLIENT_ID=<client-id>
AZURE_KEY_VAULT_CLIENT_SECRET=<client-secret>

# OR use Managed Identity (recommended):
# Set "System-assigned managed identity" in ACA → Identity blade
# AZURE_KEY_VAULT_URL is still required
```

### Frontend Configuration

```bash
# Frontend URL for OAuth redirects
FRONTEND_URL=https://your-app.azurewebsites.net  # or custom domain
CORS_ALLOWED_ORIGINS=https://your-app.azurewebsites.net,https://www.yourdomain.com
ALLOWED_HOSTS=your-app.azurewebsites.net,yourdomain.com

# OAuth Providers (optional)
GOOGLE_OAUTH_CLIENT_ID=<client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://your-app.azurewebsites.net/api/auth/google/callback/

GITHUB_OAUTH_CLIENT_ID=<client-id>
GITHUB_OAUTH_CLIENT_SECRET=<client-secret>
GITHUB_OAUTH_REDIRECT_URI=https://your-app.azurewebsites.net/api/auth/github/callback/
```

### Observability & Monitoring

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
SENTRY_DSN=<optional-for-error-tracking>

# Prometheus Metrics (built-in)
PROMETHEUS_ENABLED=True

# Application Insights (Azure)
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
```

## Deployment Steps

### 1. Create Azure Container Registry

```bash
az acr create --resource-group <rg-name> --name <registry-name> --sku Basic
az acr login --name <registry-name>
```

### 2. Build and Push Docker Image

```bash
# From repository root
docker build -f apps/backend/Dockerfile -t <registry>.azurecr.io/verirag:latest .
docker push <registry>.azurecr.io/verirag:latest
```

### 3. Create Container App

```bash
# Create environment
az containerapp env create \
  --name verirag-env \
  --resource-group <rg-name> \
  --location eastus

# Create container app
az containerapp create \
  --name verirag-api \
  --resource-group <rg-name> \
  --environment verirag-env \
  --image <registry>.azurecr.io/verirag:latest \
  --registry-server <registry>.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --target-port 8000 \
  --ingress 'external' \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 10
```

### 4. Configure Environment Variables

```bash
# Set all environment variables from above
az containerapp update \
  --name verirag-api \
  --resource-group <rg-name> \
  --set-env-vars \
    DJANGO_SECRET_KEY=<value> \
    DATABASE_HOST=<value> \
    DATABASE_PASSWORD=<value> \
    # ... add all vars
```

### 5. Run Migrations

```bash
# Connect to container and run migrations
az containerapp exec \
  --name verirag-api \
  --resource-group <rg-name> \
  -- python manage.py migrate

# Create superuser
az containerapp exec \
  --name verirag-api \
  --resource-group <rg-name> \
  -- python manage.py createsuperuser
```

## Health Checks

### Public Health Endpoint (for ACA liveness probe)

```bash
curl https://your-app.azurewebsites.net/api/health/

# Response:
{
  "healthy": true,
  "timestamp": "2026-03-18T12:34:56Z",
  "version": "2.0.0"
}
```

### Detailed Health Check (requires authentication)

```bash
curl -H "Authorization: Bearer <jwt-token>" \
  https://your-app.azurewebsites.net/api/health/details/

# Response:
{
  "status": "ok",
  "healthy": true,
  "timestamp": "2026-03-18T12:34:56Z",
  "version": "2.0.0",
  "deployment_mode": "cloud",
  "components": {
    "postgres": { "status": "healthy", "latency_ms": 2.5 },
    "redis": { "status": "healthy", "latency_ms": 1.2 },
    "azure_keyvault": { "status": "healthy", "latency_ms": 50 },
    "azure_openai": { "status": "healthy", "latency_ms": 150 }
  }
}
```

## Graceful Shutdown

The application is configured for ACA's graceful shutdown pattern:

1. **SIGTERM received** → 30-second grace period begins
2. **New requests rejected** (gunicorn stops accepting)
3. **In-flight requests complete** (up to 30 seconds)
4. **Database connections close** (via wsgi.py handler)
5. **Celery tasks stop** (via wsgi.py handler)
6. **Container exits** with code 0

No configuration needed - it's built into the Docker image and wsgi.py.

## Scaling

### Horizontal Scaling (Replicas)

```bash
az containerapp update \
  --name verirag-api \
  --resource-group <rg-name> \
  --min-replicas 2 \
  --max-replicas 20
```

### Vertical Scaling (CPU/Memory)

```bash
az containerapp update \
  --name verirag-api \
  --resource-group <rg-name> \
  --cpu 2.0 \
  --memory 4.0Gi
```

## Monitoring

### Application Insights

```bash
# View logs (last 30 minutes)
az monitor app-insights query \
  --app verirag-insights \
  --analytics-query "requests | where timestamp > ago(30m)"

# View failures
az monitor app-insights query \
  --app verirag-insights \
  --analytics-query "requests | where success == false"
```

### Container App Monitoring

```bash
# View logs
az containerapp logs show \
  --name verirag-api \
  --resource-group <rg-name> \
  --follow

# View metrics
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.App/containerApps/verirag-api \
  --metric "HttpRequests" \
  --start-time 2026-03-18T00:00:00Z
```

## Troubleshooting

### 502 Bad Gateway

```bash
# Check if app is running
az containerapp show --name verirag-api --resource-group <rg-name>

# View logs
az containerapp logs show --name verirag-api --resource-group <rg-name>

# Common causes:
# 1. Database not reachable → Check DATABASE_HOST
# 2. Out of memory → Increase --memory
# 3. Startup failed → Check log output
```

### High Memory Usage

```bash
# Check container stats
kubectl top pod -n <namespace>  # if using ACA with kubeconfig

# Solutions:
# 1. Increase memory allocation
# 2. Add --max-requests to gunicorn (already done: 1000)
# 3. Reduce DJANGO_DATABASE_POOL_SIZE
```

### Celery Tasks Not Running

```bash
# Check Redis connectivity
redis-cli -h <redis-host> -p 6379 ping

# Check Celery status
python manage.py shell
>>> from celery import current_app
>>> current_app.control.inspect().active()
```

## Security Best Practices

✅ **Implemented in this config:**

- Database connections use TLS (SSL=True in connection string)
- Redis uses TLS (ssl=True in REDIS_URL)
- Azure Key Vault for secrets management
- Non-root container user (UID: verirag)
- No DEBUG mode in production
- CSRF protection enabled
- CORS whitelisting

⚠️ **Additional recommendations:**

- Enable Azure WAF for DDoS protection
- Use Private Endpoints for database/Redis (no public access)
- Implement rate limiting (already in code)
- Enable Container Registry scanning via Microsoft Defender
- Use GitHub Actions + signed images for deployment

## Cost Optimization

| Resource | Recommendation |
|----------|-----------------|
| **Container App** | B2 (0.5 CPU, 1GB) for dev; B4 (2 CPU, 4GB) for prod |
| **Database** | General Purpose tier; Reserved Instances for 1+ years |
| **Redis** | Basic tier for dev; Standard for prod |
| **App Insights** | Configure appropriate retention (30-730 days) |

## Next Steps

1. ✅ All infrastructure configured
2. Test locally: `docker-compose up`
3. Deploy to ACA: Follow steps above
4. Monitor Application Insights
5. Set up CI/CD (GitHub Actions → ACA)
6. Configure custom domain + SSL
7. Set up backup strategy for database

## Support

For issues:
- Check logs: `az containerapp logs show --name verirag-api --resource-group <rg> --follow`
- View health: `curl https://your-app/api/health/details/`
- Check Azure portal for resource health
- Review Application Insights for errors

