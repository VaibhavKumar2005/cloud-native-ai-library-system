# Deployment – Azure Container Apps

This guide explains how to deploy VeriRAG on Azure for research-grade reliability and cost tracking.

---

## Overview

VeriRAG deploys as containerized services on Azure Container Apps (ACA):

```
Local Development
    ↓
Docker Build (backend + frontend)
    ↓
Push to Azure Container Registry
    ↓
Deploy to Container Apps (managed Kubernetes)
    ↓
PostgreSQL (Azure Database for PostgreSQL)
    ↓
Monitoring (Application Insights + Azure Monitor)
    ↓
Ready for Research Use
```

---

## Architecture

### Infrastructure Components

```
Frontend (React)
    ↓
    Azure CDN (static assets)
    Azure Container Apps (Vite dev server)
    ↓
Backend (Django)
    ↓
    Azure Container Apps (gunicorn + celery workers)
    ↓
Data Layer
    ↓
    Azure Database for PostgreSQL (16, pgvector enabled)
    Azure Cache for Redis (query caching)
    Azure Blob Storage (PDF uploads)
    ↓
Monitoring
    ↓
    Application Insights
    Azure Monitor Alerts
    Prometheus (optional, self-hosted metrics)
```

### Cost Model (Monthly Estimate)

```
Component                    Cost      Purpose
─────────────────────────────────────────────────
Frontend Container           ~$10      Vite dev server (1 replica)
Backend Container            ~$15      Django + Celery (2 replicas)
PostgreSQL (Single Server)   ~$30      16 GB, auto-backup
Redis (Basic)                ~$10      Query caching
Blob Storage                 ~$5       PDF storage (10 GB)
Application Insights         ~$5       Monitoring & logging
Data Transfer                ~$5       Egress costs
─────────────────────────────────────────────────
SUBTOTAL                     ~$80      Monthly baseline

API Costs (Usage-Dependent)
─────────────────────────────────────────────────
Google Embeddings            $0.00006  per 1K tokens
Google Gemini Flash          $0.005    per 1K input tokens
(+ fallback: Groq LLaMA)     $0.05     per 1M tokens
─────────────────────────────────────────────────

Example Query Cost:
  - Embedding: $0.00006 (512 tokens)
  - LLM synthesis: $0.0005 (100 input, 100 output)
  - RAGAS eval: $0.001 (optional, verification)
  ─────────────────────────────────────────────
  Total per query: $0.00156 (~100 queries = $0.15)

Monthly Projection (1000 queries):
  Infrastructure: $80
  API usage: $1.50
  ─────────────────────────────────────────────
  Total: ~$82/month
```

---

## Prerequisites

### Local Setup
- Docker Desktop
- Azure CLI (`az` command)
- Terraform

### Azure Resources (Required)
- Azure subscription (free tier works for small projects)
- Azure Container Registry (for Docker images)
- Azure Database for PostgreSQL (with pgvector extension)
- Azure Cache for Redis (for query caching)
- Application Insights (for monitoring)

### API Keys (Required)
- Google Cloud API key (for embeddings + Gemini)
- Groq API key (for fallback LLM)
- Optional: GitHub OAuth credentials

---

## Step 1: Prepare Environment

### 1.1 Create `.env` File

```bash
# Backend API Configuration
DEBUG=False
SECRET_KEY=your-very-secret-key-here
ALLOWED_HOSTS=yourdomain.com,*.azurecontainerapps.io

# Database
POSTGRES_USER=postgres_user
POSTGRES_PASSWORD=strong-password-here
POSTGRES_DB=verirag_db
POSTGRES_HOST=your-server.postgres.database.azure.com
POSTGRES_PORT=5432

# APIs
GOOGLE_API_KEY=your-google-cloud-api-key
GROQ_API_KEY=your-groq-api-key

# Redis
REDIS_URL=redis://:password@your-redis.redis.cache.windows.net:6379/0

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
AZURE_STORAGE_ACCOUNT_KEY=your-storage-key
AZURE_BLOB_CONTAINER_NAME=pdfs

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=your-connection-string
```

### 1.2 Update Terraform Configuration

Edit `ops/infrastructure/terraform.tfvars`:

```hcl
location             = "eastus"  # Azure region
resource_group_name  = "verirag-rg"
environment          = "production"

# Container configuration
backend_image        = "your-registry.azurecr.io/verirag-backend:latest"
frontend_image       = "your-registry.azurecr.io/verirag-frontend:latest"

# Scaling
backend_replicas     = 2
frontend_replicas    = 1

# Database
postgres_sku         = "Standard_B2s"  # 2 vCore, 4 GB RAM
postgres_storage_gb  = 32

# Monitoring
enable_application_insights = true
```

---

## Step 2: Build Docker Images

### 2.1 Build Backend

```bash
cd apps/backend

# Build image
docker build -t verirag-backend:latest .

# Test locally
docker run -e POSTGRES_HOST=host.docker.internal \
           -e DEBUG=true \
           verirag-backend:latest
```

### 2.2 Build Frontend

```bash
cd apps/frontend

# Build image
docker build -t verirag-frontend:latest .

# Test locally
docker run -p 5173:5173 verirag-frontend:latest
```

### 2.3 Push to Azure Container Registry

```bash
# Login to ACR
az acr login --name your-registry

# Tag images
docker tag verirag-backend:latest your-registry.azurecr.io/verirag-backend:latest
docker tag verirag-frontend:latest your-registry.azurecr.io/verirag-frontend:latest

# Push
docker push your-registry.azurecr.io/verirag-backend:latest
docker push your-registry.azurecr.io/verirag-frontend:latest
```

---

## Step 3: Deploy Infrastructure with Terraform

### 3.1 Initialize & Plan

```bash
cd ops/infrastructure

# Initialize Terraform
terraform init

# Verify plan (dry-run)
terraform plan -out=tfplan

# Review output
terraform show tfplan
```

### 3.2 Apply Infrastructure

```bash
# Deploy to Azure
terraform apply tfplan

# Wait for completion (~15 minutes)
# Outputs will show:
#   - Resource group name
#   - Container Apps URLs
#   - Database endpoint
#   - Application Insights key
```

### 3.3 Save Outputs

```bash
# Export outputs for next steps
terraform output -json > outputs.json

# Or manually note:
BACKEND_URL=$(terraform output -raw backend_url)
FRONTEND_URL=$(terraform output -raw frontend_url)
POSTGRES_ENDPOINT=$(terraform output -raw postgres_endpoint)
```

---

## Step 4: Configure Database

### 4.1 Connect to PostgreSQL

```bash
# Get connection string
POSTGRES_HOST=$(terraform output -raw postgres_endpoint)

# Connect with psql
psql -h $POSTGRES_HOST -U postgres_user -d verirag_db
```

### 4.2 Initialize Database

```bash
# Apply Django migrations
python manage.py migrate

# Create superuser for admin panel
python manage.py createsuperuser

# Create pgvector extension (required for vector search)
CREATE EXTENSION IF NOT EXISTS vector;

# Verify extension
\dx

# Create vector index
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### 4.3 Verify Setup

```sql
-- Check papers table
SELECT COUNT(*) FROM papers;

-- Check chunks with vectors
SELECT id, content, embedding FROM document_chunks LIMIT 1;

-- Test similarity search
SELECT id, similarity(embedding, '[0.1, 0.2, ...]'::vector) as sim
FROM document_chunks
ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

---

## Step 5: Test Deployment

### 5.1 Health Checks

```bash
# Backend health
curl https://$BACKEND_URL/api/health

# Expected response:
# {"status": "healthy", "database": "connected", "cache": "connected"}

# Frontend availability
curl https://$FRONTEND_URL

# Expected: HTML page (React app)
```

### 5.2 API Testing

```bash
# Create test paper
curl -X POST https://$BACKEND_URL/api/papers/upload \
  -F "file=@test-paper.pdf" \
  -H "Authorization: Bearer $API_TOKEN"

# List papers
curl https://$BACKEND_URL/api/papers \
  -H "Authorization: Bearer $API_TOKEN"

# Test RAG query
curl -X POST https://$BACKEND_URL/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "query": "What is RAG?",
    "papers": [1, 2, 3]
  }'
```

### 5.3 Monitoring

```bash
# Check Application Insights logs
az monitor app-insights query \
  --resource "verirag-insights" \
  --analytics-query "requests | where timestamp > ago(1h) | count"

# Check Container Apps logs
az containerapp logs show \
  --name verirag-backend \
  --resource-group verirag-rg
```

---

## Step 6: Configure Monitoring & Alerts

### 6.1 Application Insights

Enable deep monitoring for research reproducibility:

```json
{
  "tracking_enabled": true,
  "trace_every_query": true,
  "export_ragas_metrics": true,
  "sample_responses": "all"
}
```

### 6.2 Alert Rules

```hcl
# Terraform for alerting
resource "azurerm_monitor_metric_alert" "high_failure_rate" {
  name                = "RAG-High-Error-Rate"
  resource_group_name = azurerm_resource_group.main.name
  
  scopes      = [azurerm_application_insights.main.id]
  description = "Alert when RAG query errors > 5%"
  
  criteria {
    metric_name         = "requests/failed"
    operator            = "GreaterThan"
    threshold           = 50  # 50 failures in 5 min window
    aggregation         = "Count"
    metric_namespace    = "Microsoft.Insights/components"
  }
}
```

### 6.3 Custom Metrics (Prometheus)

Optional: Export RAG-specific metrics:

```python
from prometheus_client import Counter, Histogram

# Track verification metrics
ragas_faithfulness = Histogram(
    'ragas_faithfulness_score',
    'Faithfulness score distribution',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

rejection_rate = Counter(
    'query_rejections_total',
    'Total queries rejected (low confidence)'
)
```

---

## Step 7: Continuous Deployment

### 7.1 GitHub Actions (Optional)

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker build -t verirag-backend apps/backend
          docker build -t verirag-frontend apps/frontend
      
      - name: Push to ACR
        run: |
          az acr login --name ${{ secrets.ACR_NAME }}
          docker push ${{ secrets.ACR_NAME }}/verirag-backend:latest
      
      - name: Deploy with Terraform
        run: |
          cd ops/infrastructure
          terraform apply -auto-approve
```

---

## Step 8: Production Checklist

Before using for actual research:

- [ ] Database backups enabled (automated daily)
- [ ] Monitoring & alerts configured
- [ ] SSL/TLS certificates installed
- [ ] CORS configured for your domain
- [ ] Rate limiting enabled (prevent API abuse)
- [ ] Logging retention set (30 days minimum)
- [ ] Disaster recovery plan documented
- [ ] Cost monitoring enabled (alert at $100/month)
- [ ] Load tests completed (100+ concurrent users)
- [ ] Security audit passed (no secrets in code)

---

## Troubleshooting

### Container Apps Won't Start

```bash
# Check container logs
az containerapp logs show --name verirag-backend --resource-group verirag-rg

# Common issues:
# - Missing environment variables
# - Database connection timeout
# - Invalid API keys
```

### Database Connection Fails

```bash
# Verify network connectivity
az postgres server show --resource-group verirag-rg --name your-server

# Check firewall rules (must allow Container Apps IP)
az postgres server firewall-rule list --resource-group verirag-rg

# Add Container Apps IP if needed
az postgres server firewall-rule create \
  --resource-group verirag-rg \
  --server-name your-server \
  --name AllowContainerApps \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

### API Keys Not Working

```bash
# Verify Google API key
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY"

# Verify Groq API key
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

---

## Cost Optimization

### Reduce Infrastructure Costs

```hcl
# Use cheaper Database SKU for dev
postgres_sku = "Standard_B1s"  # $15/month instead of $30

# Single backend replica (no high availability)
backend_replicas = 1

# Disable Application Insights in dev
enable_application_insights = false
```

### Reduce API Costs

```python
# Implement aggressive caching
CACHE_TTL = 86400  # 24 hours

# Skip RAGAS for low-confidence answers
if confidence < 0.70:
    return rejection()  # Don't pay for RAGAS eval
else:
    run_ragas_evaluation()  # Only when confident
```

---

## Research-Grade Considerations

### Reproducibility
- All deployment parameters in Terraform
- Environment vars tracked in secure vault
- Container images tagged with commit hash
- Deployment date logged in Application Insights

### Auditability
- All API calls logged to Application Insights
- Query/response pairs stored for review
- Verification metrics exportable to CSV
- Monthly reports generated automatically

### Reliability
- Automatic failover for database
- Multi-replica backend (if budget allows)
- Redis for caching (reduces API costs 50%)
- Graceful fallback (Gemini → Groq)

---

## Next Steps

1. **Deploy and test** the stack
2. **Upload research papers** (5-10 to start)
3. **Run evaluation tests** (see `docs/evaluation.md`)
4. **Review monitoring** (Application Insights)
5. **Refine based on metrics** (iterate on system)

---

See also: [RAG Pipeline](rag_pipeline.md), [Evaluation](evaluation.md), [Ingestion](ingestion.md)
