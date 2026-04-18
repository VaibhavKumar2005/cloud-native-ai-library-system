# VeriRAG Academic - Docker & Azure Deployment Guide

## Current Status (April 18, 2026)

### ✅ Completed

- Frontend: Academic Dashboard with search, analysis, library, and topic explorer
- Backend Models: Academic papers, research libraries, gaps, topics, Q&A
- API Endpoints: Semantic Scholar, arXiv, CrossRef integration
- Serializers: All models have DRF serializers
- Authentication: JWT-based user isolation

### ⏳ Next Steps

1. Create Django migrations for new academic models
2. Update URL routing for academic endpoints
3. Enhance RAG logic for academic papers
4. Test full system in Docker
5. Deploy to Azure Container Apps

---

## Docker Setup & Local Testing

### Prerequisites

```bash
# Install Docker Desktop (required)
# No Node.js needed - frontend runs in Docker

# Verify Docker is running
docker --version
docker-compose --version
```

### Step 1: Generate Database Migrations

```bash
# Inside the backend container
docker exec -it rag-backend python manage.py makemigrations ai_engine

# Apply migrations
docker exec -it rag-backend python manage.py migrate
```

### Step 2: Start the Full System

```bash
# From project root
cd "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"

# Start all services
docker-compose up -d --build

# Check status
docker-compose ps

# Expected output:
# ✅ rag-vault      - Running (seed endpoint)
# ✅ rag-db         - Running (PostgreSQL + pgvector)
# ✅ rag-redis      - Running (Celery broker)
# ✅ rag-backend    - Running (Django API)
# ✅ rag-frontend   - Running (React app)
# ✅ rag-celery-worker - Running (Async tasks)
# ✅ rag-celery-beat   - Running (Scheduled tasks)
```

### Step 3: Access the Application

| Service | URL | Purpose |
| --- | --- | --- |
| **Frontend** | [http://localhost:5173](http://localhost:5173) | React dashboard |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | Django REST API |
| **Admin Panel** | [http://localhost:8000/admin](http://localhost:8000/admin) | Django admin |
| **API Docs** | [http://localhost:8000/api/schema/swagger-ui](http://localhost:8000/api/schema/swagger-ui) | Swagger UI |
| **Metrics** | [http://localhost:9090](http://localhost:9090) | Prometheus (optional) |

### Step 4: Create Admin User

```bash
docker exec -it rag-backend python manage.py createsuperuser
# Follow prompts (username: admin, password: admin123)
```

### Step 5: Test Academic Paper API

```bash
# 1. Login to http://localhost:5173
# 2. Navigate to /research (Academic Dashboard)
# 3. Click "Search Papers" tab
# 4. Search for "prompt engineering"
# 5. Add papers to library
# 6. Analyze research gaps
# 7. Get topic recommendations

# Or test via curl:
# Get JWT token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Search papers (replace TOKEN with your JWT)
curl -X POST http://localhost:8000/api/papers/search/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "prompt engineering", "source": "semantic-scholar"}'
```

### Step 6: View Logs

```bash
# All containers
docker-compose logs -f

# Specific service
docker-compose logs -f rag-backend
docker-compose logs -f rag-celery-worker
docker-compose logs -f rag-frontend
```

### Step 7: Stop Everything

```bash
docker-compose down

# Remove volumes (clean database)
docker-compose down -v
```

---

## Testing Checklist

### Frontend Tests

- [ ] Login with admin credentials
- [ ] Navigate to /research (Academic Dashboard)
- [ ] Search papers via Semantic Scholar
- [ ] Add papers to library
- [ ] View paper library
- [ ] Ask questions about papers
- [ ] View research gaps
- [ ] Get topic recommendations

### Backend Tests

- [ ] Verify JWT authentication works
- [ ] Check paper search from multiple sources
- [ ] Verify paper ingestion to database
- [ ] Test RAG Q&A on papers
- [ ] Check Celery tasks execute
- [ ] Monitor metrics/logs

### Database Tests

- [ ] Verify academic_paper table created
- [ ] Check papers are multi-tenant (filtered by user)
- [ ] Verify pgvector extension loaded
- [ ] Run vector search test

```bash
# Inside rag-db container
docker exec -it rag-db psql -U admin -d verirag_db

# In PostgreSQL:
SELECT * FROM ai_engine_academicpaper LIMIT 5;
SELECT * FROM ai_engine_paperlibrary LIMIT 5;
```

---

## Common Issues & Fixes

### Issue: Docker image build fails

```bash
# Clean rebuild
docker-compose down -v
docker system prune -a
docker-compose up -d --build
```

### Issue: postgres service won't start

```bash
# Check logs
docker-compose logs rag-db

# Rebuild
docker-compose down -v
docker-compose up -d --build rag-db
```

### Issue: Frontend shows blank page

```bash
# Clear browser cache
# Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# Check frontend logs
docker-compose logs rag-frontend

# Rebuild frontend
docker-compose up -d --build rag-frontend
```

### Issue: API endpoints return 404

```bash
# Verify backend is running
docker exec rag-backend curl http://localhost:8000/api/
# Should return JSON

# Check URL routing
# Endpoints should be under /api/papers/*
```

---

## Azure Container Apps Deployment

Once Docker testing is complete:

### Step 1: Prepare Azure Resources

```bash
# Set environment variables
$RESOURCE_GROUP = "verirag-rg"
$LOCATION = "eastus"
$REGISTRY_NAME = "veriracontainerregistry"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create container registry
az acr create --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME --sku Basic
```

### Step 2: Build and Push Images

```bash
# Login to ACR
az acr login --name $REGISTRY_NAME

# Build and push backend
docker build -t verirag-backend:latest ./apps/backend
docker tag verirag-backend:latest $REGISTRY_NAME.azurecr.io/verirag-backend:latest
docker push $REGISTRY_NAME.azurecr.io/verirag-backend:latest

# Build and push frontend
docker build -t verirag-frontend:latest ./apps/frontend --build-arg VITE_API_URL=https://yourdomain.com
docker tag verirag-frontend:latest $REGISTRY_NAME.azurecr.io/verirag-frontend:latest
docker push $REGISTRY_NAME.azurecr.io/verirag-frontend:latest
```

### Step 3: Create Container App Environment

```bash
# Create environment with Log Analytics
$LOG_WORKSPACE_ID = az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name "verirag-logs" \
  --query id -o tsv

# Create environment
az containerapp env create \
  --name verirag-env \
  --resource-group $RESOURCE_GROUP \
  --logs-workspace-id $LOG_WORKSPACE_ID \
  --location $LOCATION
```

### Step 4: Deploy Backend Container App

```bash
az containerapp create \
  --name verirag-backend \
  --resource-group $RESOURCE_GROUP \
  --environment verirag-env \
  --image $REGISTRY_NAME.azurecr.io/verirag-backend:latest \
  --target-port 8000 \
  --ingress 'external' \
  --registry-server $REGISTRY_NAME.azurecr.io \
  --registry-username $REGISTRY_ADMIN_USERNAME \
  --registry-password $REGISTRY_ADMIN_PASSWORD \
  --env-vars \
    DJANGO_SECRET_KEY="your-secret" \
    DEBUG="False" \
    POSTGRES_HOST="your-azure-postgres" \
    ALLOWED_HOSTS="yourdomain.com" \
  --cpu 0.5 --memory 1.0Gi \
  --scale-rule-custom \
    name=cpu-scale \
    trigger-type=cpu \
    metadata="{threshold: '70'}"
```

### Step 5: Deploy Frontend Container App

```bash
az containerapp create \
  --name verirag-frontend \
  --resource-group $RESOURCE_GROUP \
  --environment verirag-env \
  --image $REGISTRY_NAME.azurecr.io/verirag-frontend:latest \
  --target-port 80 \
  --ingress 'external' \
  --registry-server $REGISTRY_NAME.azurecr.io \
  --registry-username $REGISTRY_ADMIN_USERNAME \
  --registry-password $REGISTRY_ADMIN_PASSWORD
```

### Step 6: Setup Database (Azure Database for PostgreSQL)

```bash
# Create PostgreSQL server with pgvector
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name verirag-postgres \
  --location $LOCATION \
  --admin-user admin \
  --admin-password "YourSecurePassword123!" \
  --sku-name Standard_B2s \
  --storage-size 32

# Enable pgvector extension
az postgres flexible-server parameter set \
  --name shared_preload_libraries \
  --value "pgvector" \
  --resource-group $RESOURCE_GROUP \
  --server-name verirag-postgres

# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name verirag-postgres \
  --database-name verirag_db
```

### Step 7: Run Migrations on Azure

```bash
# Get connection string from Azure Portal
$CONNECTION_STRING = "your-connection-string"

# Run migrations (from Container App terminal)
docker run --rm \
  -e DATABASE_URL="$CONNECTION_STRING" \
  $REGISTRY_NAME.azurecr.io/verirag-backend:latest \
  python manage.py migrate
```

---

## Cost Monitoring ($97/Month Budget)

### Azure Container Apps Pricing

- **Backend**: 0.5 CPU, 1GB RAM ≈ $10-15/month
- **Frontend**: 0.25 CPU, 0.5GB RAM ≈ $5-10/month
- **PostgreSQL**: Basic tier ≈ $30-40/month
- **Redis**: Cache for Celery ≈ $10-15/month
- **Monitor/Logging**: ≈ $5-10/month

### Total Cost: ~$60-90/month (within budget)

### Cost Optimization Tips

1. Use KEDA scale-to-zero for backend (scale down when idle)
2. Use PostgreSQL Basic tier (sufficient for academic papers)
3. Cache API responses (Semantic Scholar, arXiv)
4. Monitor metrics in Azure Monitor
5. Use Reserved Instances for predictable workloads

---

## Next Steps After Deployment

1. **Setup Custom Domain**: Point yourdomain.com to Container App
2. **Enable HTTPS**: Auto-managed by Azure
3. **Setup CI/CD**: GitHub Actions for auto-deploy
4. **Monitoring**: Set up alerts for errors, latency
5. **Backup**: Configure automated PostgreSQL backups
6. **Security**: Enable Managed Identity, Network Security Groups

---

## Support & Troubleshooting

### Docker Issues

- Run `docker-compose logs` for detailed errors
- Check disk space: `docker system df`
- Reset: `docker-compose down -v && docker system prune -a`

### Azure Issues

- Check Azure Portal > Container Apps
- View logs in Log Analytics workspace
- Use `az containerapp logs show` for debugging

### Performance Issues

- Monitor CPU/Memory in Azure Monitor
- Check slow queries in PostgreSQL
- Profile with Ray/cProfile
- Optimize vector search queries

---

## References

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [React Deployment](https://vite.dev/)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
