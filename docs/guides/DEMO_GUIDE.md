# 🎯 VeriRAG Live Demo Guide

> **Complete preparation checklist for showcasing your production-grade RAG system**

This guide ensures your VeriRAG system is demo-ready with:
- ✅ All services healthy and connected
- ✅ PDF upload and vector indexing working
- ✅ Frontend-backend integration verified
- ✅ System metrics visible
- ✅ Cost-controlled Azure deployments

---

## 📋 Pre-Demo Checklist (15 minutes)

### Step 1: Environment Setup (5 min)

```powershell
# Navigate to project root
cd "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"

# Verify Docker is running
docker ps
# Expected: Should return running containers or empty list (not error)

# Start all services
docker-compose up -d

# Wait for services to initialize (critical!)
Start-Sleep -Seconds 45
```

**Why 45 seconds?** PostgreSQL needs time to:
1. Initialize pgvector extension
2. Accept connections
3. Run Django migrations

### Step 2: Vault Initialization (2 min)

```powershell
# Check if Vault is already initialized
docker exec rag-vault vault status

# If sealed or uninitialized, run:
.\scripts\setup\init_vault.ps1

# OR manually unseal:
docker exec rag-vault vault operator unseal <YOUR_UNSEAL_KEY>
docker exec rag-vault vault login <YOUR_ROOT_TOKEN>
```

**Store your API keys in Vault:**
```powershell
# Set your API keys (replace with real keys)
$env:GOOGLE_API_KEY = "AIzaSy..."  # From https://aistudio.google.com/
$env:GROQ_API_KEY = "gsk_..."     # From https://console.groq.com/

# Inject into Vault
docker exec -i rag-vault vault kv put secret/myapp `
  GOOGLE_API_KEY="$env:GOOGLE_API_KEY" `
  GROQ_API_KEY="$env:GROQ_API_KEY"
```

### Step 3: Database Setup (3 min)

```powershell
# Activate Python virtual environment
& .\.venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Run migrations
python manage.py migrate --noinput

# Setup pgvector extension
python setup_pgvector.py

# Create superuser for demo (optional)
# python manage.py createsuperuser --noinput --username demo --email demo@verirag.dev
```

### Step 4: Health Verification (5 min)

```powershell
# Run comprehensive health check script
.\scripts\demo\demo-health-check.ps1

# Expected output:
# ✅ Docker Services Running
# ✅ Vault Unsealed
# ✅ Database Connected
# ✅ Redis Available
# ✅ Backend API Responding
# ✅ Frontend Accessible
```

---

## 🚀 Demo Flow (10-15 minutes)

### Act 1: System Architecture Overview (3 min)

**Show the running infrastructure:**
```powershell
# Display all running services
docker-compose ps

# Show container resource usage
docker stats --no-stream
```

**Key Points to Highlight:**
- 🏗️ **Microservices Architecture**: Backend, Frontend, DB, Redis, Vault, Celery, Monitoring
- 🔒 **Security-First**: Vault for secrets, JWT auth, non-root containers
- 📊 **Observable**: Prometheus + Grafana metrics, OpenTelemetry tracing
- ⚡ **Async Processing**: Celery for background PDF ingestion

**Open Architecture Diagram:**
```powershell
code docs\showcase\ARCHITECTURE.md
```

---

### Act 2: Document Upload & Vector Indexing (4 min)

**Open Frontend Dashboard:**
```powershell
# Start browser at frontend
Start-Process "http://localhost:8080"
```

**Demo Login:**
- Create a test user OR use existing credentials
- Navigate to Dashboard

**Upload a PDF:**
1. Click **"Upload Document"** button
2. Select a technical PDF (e.g., `docs/assets/demo/test-document.pdf`)
3. Show the upload progress indicator

**Behind the Scenes Explanation:**
```
User uploads PDF → Django API receives file
                 ↓
              Celery worker picks up task
                 ↓
         PyPDFLoader extracts text
                 ↓
    RecursiveCharacterTextSplitter chunks text
                 ↓
   GoogleGenerativeAIEmbeddings generates vectors (768-dim)
                 ↓
          Stored in pgvector database
```

**Verify in Database:**
```powershell
# Show documents in database
docker exec -it rag-db psql -U admin -d verirag_db -c `
  "SELECT id, title, created_at FROM ai_engine_document ORDER BY created_at DESC LIMIT 5;"
```

**Check Celery Logs:**
```powershell
# Show real-time ingestion logs
docker logs -f rag-celery-worker --since 5m
```

---

### Act 3: RAG Query with Verification (5 min)

**Ask AI a Question:**
1. In the Dashboard, type a question related to your uploaded PDF
2. Example: *"What are the main security features described in this document?"*

**Show the Response Structure:**
```json
{
  "answer": "Based on the document, the main security features include...",
  "faithfulness_score": 0.85,
  "verification_status": "VERIFIED ✓",
  "sources": [
    {
      "page": 3,
      "text": "Security is implemented via..."
    }
  ],
  "model_used": "gemini-1.5-flash",
  "response_time_ms": 2340
}
```

**Explain the Verification Process:**
```
1. Question → Vector similarity search in pgvector
2. Retrieve top 5 relevant chunks
3. Gemini generates answer with citations
4. Critic Agent scores faithfulness (0-1)
5. If score < 0.6 → ❌ REJECT → Failover to Groq/Llama-3
6. If score ≥ 0.6 → ✅ ACCEPT → Return to user
```

**Show Prometheus Metrics:**
```powershell
# Open Prometheus UI
Start-Process "http://localhost:9090"

# Query: verirag_hallucination_rejections_total
# Query: verirag_llm_fallbacks_total
# Query: verirag_query_duration_seconds
```

---

### Act 4: System Monitoring & Observability (3 min)

**Open Monitoring Dashboard:**
```powershell
Start-Process "http://localhost:3000"  # Grafana
# Default: admin/admin
```

**Show Key Metrics:**
- 📈 **Query Latency**: P50, P95, P99 response times
- 🔥 **Throughput**: Queries per second
- ❌ **Error Rate**: Failed queries / total queries
- 🚨 **Hallucination Rate**: Rejected responses / total responses
- 🔄 **LLM Failovers**: Gemini → Groq fallback count

**Navigate Frontend Analytics:**
- Go to `/analytics` route in React app
- Show real-time system insights
- Display faithfulness distribution chart

---

### Act 5: Cloud Deployment (Optional - Only if Demoing Azure)

**Build and Push to Azure Container Registry:**
```powershell
# Build images locally (no cost)
docker-compose build

# Tag for ACR
docker tag verirag-backend:latest yourregistry.azurecr.io/verirag-backend:demo
docker tag verirag-frontend:latest yourregistry.azurecr.io/verirag-frontend:demo

# Login to ACR
az acr login --name yourregistry

# Push (incurs minimal egress cost)
docker push yourregistry.azurecr.io/verirag-backend:demo
docker push yourregistry.azurecr.io/verirag-frontend:demo
```

**Manual Deploy to Azure Container Apps:**
```powershell
# Trigger GitHub Actions workflow manually (only when you want to deploy)
# Go to: https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/actions
# Select "VeriRAG CI/CD Pipeline"
# Click "Run workflow" → Select branch: main → Run
```

**Important:** The CI/CD pipeline now only deploys on **manual workflow_dispatch** trigger, not on every push. This saves Azure credits by preventing unnecessary deployments during development.

---

## 🎨 Demo Talking Points (System Design Highlights)

### 1. **Microservices Architecture**
- "Each component is independently scalable"
- "Backend can scale horizontally without affecting workers"
- "Stateless design enables blue-green deployments"

### 2. **Security Best Practices**
- "Secrets never in environment variables - all in Vault"
- "JWT authentication with refresh tokens"
- "Non-root container users (AZ-400 compliant)"
- "CSP headers and CORS restrictions"

### 3. **Hallucination Resistance**
- "Dual-agent verification system"
- "Faithfulness scoring on every response"
- "Automatic failover to backup LLM"
- "Citation tracking for transparency"

### 4. **Production-Grade Observability**
- "Custom Prometheus metrics for AI operations"
- "OpenTelemetry distributed tracing"
- "Health checks on all services"
- "Structured logging for debugging"

### 5. **Cloud-Native Design**
- "Multi-stage Docker builds for efficiency"
- "Kubernetes manifests for orchestration"
- "Terraform IaC for reproducible infrastructure"
- "GitOps with ArgoCD for deployments"

### 6. **Performance Optimization**
- "Async task processing with Celery"
- "Vector similarity search with pgvector (HNSW index)"
- "Redis caching for Vault secrets"
- "Connection pooling for database"

### 7. **Cost Efficiency**
- "Manual deployment triggers (no wasted credits)"
- "Spot instances compatible (stateless workers)"
- "Vertical pod autoscaling based on memory"
- "Efficient embeddings (768-dim vs 1536-dim)"

---

## 🐛 Troubleshooting During Demo

### Issue: "Backend API unreachable"
```powershell
# Check backend logs
docker logs rag-backend --tail 50

# Restart backend
docker-compose restart rag-backend

# Verify port binding
netstat -an | Select-String "8000"
```

### Issue: "PDF upload fails"
```powershell
# Check Celery worker logs
docker logs rag-celery-worker --tail 50

# Verify Vault is unsealed
docker exec rag-vault vault status

# Restart worker
docker-compose restart rag-celery-worker
```

### Issue: "Low faithfulness scores"
- This is actually a **feature demo opportunity!**
- Show the rejection log in Prometheus
- Demonstrate the automatic Groq failover
- Explain the strict verification threshold

### Issue: "Frontend not loading"
```powershell
# Check if frontend container is running
docker ps | Select-String "frontend"

# Check nginx logs
docker logs rag-frontend --tail 50  # If using compose override

# Verify API URL in frontend
docker exec -it <frontend-container> cat /usr/share/nginx/html/assets/index*.js | Select-String "localhost:8000"
```

### Issue: "Database connection errors"
```powershell
# Check PostgreSQL status
docker exec -it rag-db pg_isready -U admin

# Verify pgvector extension
docker exec -it rag-db psql -U admin -d verirag_db -c "SELECT * FROM pg_extension WHERE extname='vector';"

# Check connection from backend
docker exec -it rag-backend python manage.py dbshell
```

---

## 💰 Cost Management

### Local Development (Free)
- All services run locally in Docker
- Only uses your machine resources
- No cloud costs

### Azure Demo Environment (Controlled)
**Current Setup:**
- ✅ Manual deployment only (workflow_dispatch)
- ✅ No auto-deploy on every commit
- ✅ You control when containers are updated

**Cost Breakdown (Estimated):**
- Azure Container Apps: ~$10-30/month (depends on usage)
- Azure Container Registry: ~$5/month (Basic tier)
- Azure Cache for Redis: ~$15/month (Basic C0)
- Azure PostgreSQL Flexible: ~$20/month (Burstable B1ms)

**Total: ~$50-70/month** if running 24/7

### Cost Optimization Tips:
1. **Stop when not demoing:**
   ```powershell
   # Scale to zero
   az containerapp update --name ca-verirag-dev-backend --resource-group rg-verirag-dev --min-replicas 0 --max-replicas 0
   ```

2. **Use Free Tier Services:**
   - GitHub Actions: 2,000 minutes/month free
   - Azure Container Registry: Basic tier is sufficient
   - Azure DevTest subscriptions (if eligible)

3. **Deploy only for live demos:**
   - Keep working locally
   - Deploy to Azure 1 day before demo
   - Tear down after demo (or scale to zero)

---

## 📊 Success Metrics for Demo

During your demo, you should see:

| Metric | Target | Location |
|--------|--------|----------|
| Backend Response Time | < 3 seconds | Network tab, Prometheus |
| Faithfulness Score | > 0.6 (avg) | API response, Analytics |
| Hallucination Rejection Rate | < 20% | Prometheus metrics |
| Vector Search Time | < 500ms | Backend logs |
| Container Health | 100% healthy | `docker ps` |
| Zero Downtime | No 5xx errors | Health checks |

---

## 🎯 Pre-Demo Dry Run (Recommended)

**24 hours before demo:**
1. ✅ Run full setup from scratch
2. ✅ Upload 3-5 test PDFs
3. ✅ Run 10 test queries
4. ✅ Verify all metrics are visible
5. ✅ Check Azure deployment (if applicable)
6. ✅ Take screenshots of key screens
7. ✅ Prepare backup laptop (Murphy's Law!)

**1 hour before demo:**
1. ✅ Restart all Docker services (fresh state)
2. ✅ Run `.\scripts\demo\demo-health-check.ps1`
3. ✅ Open all browser tabs (Dashboard, Prometheus, Grafana)
4. ✅ Have API keys ready (if re-initializing Vault)
5. ✅ Close unnecessary applications
6. ✅ Turn off notifications

---

## 📚 Additional Resources

- **Architecture**: See `docs/showcase/ARCHITECTURE.md`
- **API Docs**: See `docs/API_SPEC.md`
- **Security**: See `../reports/SECURITY_REMEDIATION.md`
- **Testing**: See `TESTING_GUIDE.md`

---

## 🆘 Emergency Contacts

If something goes wrong during live demo:

1. **Fallback to slides**: Always have a backup presentation
2. **Use recorded video**: Pre-record a demo video as backup
3. **Local vs Cloud**: If Azure fails, switch to local demo

---

## 🎬 Closing the Demo

**Final Talking Points:**
- "This system is production-ready with security scans passing"
- "All code is open source on GitHub"
- "Infrastructure is reproducible via Terraform"
- "Deployed on Azure Container Apps with Kubernetes orchestration"
- "Implements AZ-400 and cloud-native best practices"

**Thank You Slide:**
- GitHub: https://github.com/VaibhavKumar2005/cloud-native-ai-library-system
- Architecture Diagrams: Available in `/docs`
- Live System (if deployed): https://your-container-app-url.azurecontainerapps.io

---

**Good luck with your demo! 🚀**

---

**Created**: March 8, 2026  
**Maintainer**: VeriRAG Team 96  
**Next Review**: Before each demo
