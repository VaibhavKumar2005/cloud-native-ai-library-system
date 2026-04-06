# Local Development & Testing Guide

> **Set up VeriRAG on your local machine for development**

---

## 🎯 Prerequisites

- **Python:** 3.11+
- **Node.js:** 18+ (for frontend)
- **Docker Desktop:** Latest (for Postgres + Redis)
- **Git:** Latest

---

## 🚀 Quick Start (5 minutes)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
cd "Azure Cloud Native RAG"

# Create Python virtual environment
python -m venv .venv

# Activate venv
# On macOS/Linux:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
# Backend
cd apps/backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 3. Start Local Services

```bash
# Start Docker services (Postgres + Redis)
docker-compose up -d

# Wait 10 seconds for services to be ready
sleep 10

# Verify services
docker-compose ps
```

### 4. Run Backend

```bash
cd apps/backend

# Apply migrations
python manage.py migrate

# Load initial data (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver 0.0.0.0:8000
```

Backend is now at: `http://localhost:8000`

### 5. Run Frontend

```bash
cd apps/frontend

# Start dev server
npm run dev
```

Frontend is now at: `http://localhost:5173`

---

## 🧪 Testing

### Run Backend Tests

```bash
cd apps/backend

# All tests
pytest

# Specific test file
pytest tests/test_rag_query.py

# With coverage
pytest --cov=ai_engine tests/

# Verbose output
pytest -v tests/
```

### Run Frontend Tests

```bash
cd apps/frontend

# Run all tests
npm test

# Watch mode (re-run on changes)
npm test -- --watch
```

### Integration Testing (Local)

```bash
cd apps/backend

# Test LLM connections
python test_llm.py

# Test pgvector setup
python setup_pgvector.py

# Validate system
python validate_changes.py
```

---

## 🔑 Configuration

### Backend (`.env`)

```bash
# Create apps/backend/.env
cat > apps/backend/.env << 'EOF'
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here-dev-only
ALLOWED_HOSTS=localhost,127.0.0.1,localhost:3000

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/verirag

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM Configuration
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
OPENAI_API_KEY=your-openai-key
DEFAULT_LLM_MODEL=gemini-2.0-flash
BACKUP_LLM_MODEL=groq-llama3

# RAG Configuration
SIMILARITY_THRESHOLD=0.7
TOP_K_RETRIEVED_DOCS=5

# Critic Agent
CRITIC_CONFIDENCE_THRESHOLD=0.75
AUTO_FAILOVER_ENABLED=True

# CostOps
COSTOPS_ENABLED=True
MONTHLY_BUDGET=1000
COST_LOG_PATH=/tmp/verirag_costs.jsonl

# QualityOps
QUALITYOPS_ENABLED=True
QUALITY_LOG_PATH=/tmp/verirag_quality.jsonl

# JWT
JWT_SECRET_KEY=your-jwt-secret-dev
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
EOF
```

### Frontend (`.env`)

```bash
# Create apps/frontend/.env
cat > apps/frontend/.env << 'EOF'
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=VeriRAG Local Dev
VITE_DEBUG=true
EOF
```

---

## 📊 Architecture Overview (Local)

```
┌─────────────────────────────────────────────────────────┐
│         Frontend (React + Vite)                         │
│         http://localhost:5173                           │
└──────────────────┬──────────────────────────────────────┘
                   │ JWT Auth
                   ▼ http://localhost:8000
┌─────────────────────────────────────────────────────────┐
│         Backend (Django REST)                           │
│         ├─ RAG Engine (Gemini + Groq failover)          │
│         ├─ Critic Agent (faithfulness verification)     │
│         ├─ CostOps (cost tracking)                      │
│         └─ QualityOps (quality gates)                   │
└────___────┬──────────────┬────────────────────┬─────────┘
            │              │                    │
            ▼              ▼                    ▼
      ┌─────────────┐ ┌────────┐ ┌──────────────────┐
      │ PostgreSQL  │ │ Redis  │ │ LLM APIs         │
      │ :5432       │ │ :6379  │ │ (Gemini/Groq)    │
      └─────────────┘ └────────┘ └──────────────────┘
```

---

## 🐛 Debugging

### Enable Verbose Logging

```bash
# Backend
export DJANGO_LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1
python manage.py runserver --verbosity 3

# Frontend
npm run dev -- --debug
```

### Connect to Databases

```bash
# PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/verirag

# Redis CLI
redis-cli -h localhost -p 6379

# View databases
redis-cli INFO stats
```

### Common Issues

#### "Connection refused" on Backend startup
```bash
# Check if services are running
docker-compose ps

# If not running:
docker-compose up -d

# Check logs
docker-compose logs postgres
```

#### "ModuleNotFoundError" in Python
```bash
# Ensure venv is activated
which python  # Should show .venv path

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

#### "CORS error" in Frontend
```bash
# Ensure ALLOWED_HOSTS includes frontend URL
# In .env:
ALLOWED_HOSTS=localhost,127.0.0.1,localhost:3000,localhost:5173

# Restart backend
python manage.py runserver
```

---

## 🔄 Workflow: Making Changes

### Adding a Model Migration

```bash
# Make changes to apps/backend/*/models.py
vim apps/backend/ai_engine/models.py

# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate

# Test it
pytest tests/test_models.py
```

### Adding an API Endpoint

```bash
# 1. Add view in apps/backend/ai_engine/views.py
# 2. Add URL routing in apps/backend/ai_engine/urls.py
# 3. Test with:
pytest tests/test_api.py -v

# Or curl:
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/your-endpoint/
```

### Updating Frontend Component

```bash
# 1. Edit: apps/frontend/src/components/YourComponent.jsx
# 2. Hot reload automatically updates (Vite watches files)
# 3. Check browser console for errors

# Or run tests:
npm test -- YourComponent.test.jsx
```

---

## 📈 Testing RAG Pipeline

### Manual RAG Query Test

```bash
cd apps/backend

python manage.py shell
```

```python
from ai_engine.rag_logic import RAGEngine

engine = RAGEngine()

# Upload a PDF (if not already done)
engine.ingest_document("docs/my_research_paper.pdf")

# Query with verification
result = engine.query(
    "What is pgvector?",
    verify_response=True,
    failover_enabled=True
)

print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
print(f"Citations: {result['citations']}")
print(f"Cost: ${result['cost']:.4f}")
```

### Test Cost Tracking

```python
from ai_engine.costops import get_cost_tracker

tracker = get_cost_tracker()
today_cost = tracker.get_daily_total()
month_cost = tracker.get_monthly_total()

print(f"Today: ${today_cost:.2f}")
print(f"This month: ${month_cost:.2f}")
```

### Test Quality Gates

```python
from ai_engine.qualityops import get_quality_gate

gate = get_quality_gate()
quality = gate.evaluate_response(
    request_id="test-001",
    query="What is pgvector?",
    answer="pgvector is...",
    contexts=["context1", "context2"],
    ragas_scores={"faithfulness": 0.92, "answer_relevancy": 0.88}
)

print(f"Quality tier: {quality['tier']}")
print(f"Passed gate: {quality['passed']}")
```

---

## 🧹 Cleanup

### Stop Services

```bash
# Stop all containers
docker-compose down

# Deactivate virtual environment
deactivate
```

### Reset Database

```bash
# WARNING: This deletes all data
docker-compose down -v

# Then restart:
docker-compose up -d
python manage.py migrate
```

### Clean Caches

```bash
# Clear Redis
redis-cli FLUSHALL

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

---

## 📝 Code Style & Standards

### Python (Backend)

```bash
# Format code (Black)
black apps/backend/

# Lint (Flake8)
flake8 apps/backend/ --max-line-length=100

# Type checking (Mypy)
mypy apps/backend/
```

### JavaScript (Frontend)

```bash
# Format code (Prettier)
npm run format

# Lint (ESLint)
npm run lint

# Fix linting issues
npm run lint -- --fix
```

---

## 🚀 Running Specific Test Suites

```bash
# Test RAG engine
pytest tests/test_rag_engine.py -v

# Test Critic Agent
pytest tests/test_critic_agent.py -v

# Test CostOps
pytest tests/test_costops.py -v

# Test QualityOps
pytest tests/test_qualityops.py -v

# Test API endpoints
pytest tests/test_api_endpoints.py -v

# Only run tests that haven't been run recently
pytest --lastfailed
```

---

## 📚 Useful Commands Reference

| Task | Command |
|------|---------|
| Start all services | `docker-compose up -d` |
| View service logs | `docker-compose logs -f backend` |
| Stop services | `docker-compose down` |
| Run migrations | `python manage.py migrate` |
| Create superuser | `python manage.py createsuperuser` |
| Access admin | `http://localhost:8000/admin` |
| Run tests | `pytest` |
| Frontend dev server | `npm run dev` |
| Build frontend | `npm run build` |
| Backend API docs | `http://localhost:8000/api/docs/` |

---

## 🔐 Security Notes

⚠️ **Local Dev Only Settings:**
- `DEBUG=True` (never in production)
- Hardcoded secrets in `.env` (use Key Vault in prod)
- `ALLOWED_HOSTS=localhost` (restrict in prod)
- No HTTPS (use in prod)

---

**Last Updated:** April 6, 2026  
**Python:** 3.11+  
**Node.js:** 18+
