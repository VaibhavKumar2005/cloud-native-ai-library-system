<p align="center">
  <img src="https://img.shields.io/badge/Team-96-blueviolet?style=for-the-badge" alt="Team 96" />
  <img src="https://img.shields.io/badge/VeriRAG-AI%20Librarian-emerald?style=for-the-badge" alt="VeriRAG" />
  <img src="https://img.shields.io/badge/Azure-Cloud%20Native-0078D4?style=for-the-badge&logo=microsoftazure" alt="Azure" />
</p>

# 📚 VeriRAG — The Azure-Native AI Librarian

> **A cloud-native, hallucination-resistant Retrieval-Augmented Generation (RAG) platform with dual-agent verification, built for production on Azure Kubernetes Service.**

VeriRAG is an intelligent document library system that ingests PDFs, converts them to vector embeddings, and answers user questions with **verified, citation-backed responses**. Every AI-generated answer passes through a **Critic Agent** that scores faithfulness against the source material. If the score falls below a configurable threshold, the system automatically fails over to a backup LLM and regenerates the response.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                        │
│   Dashboard  ·  Mission Control  ·  Analytics  ·  Bento Grid UI       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ JWT Auth (SimpleJWT)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (Django REST Framework)                   │
│                                                                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Document │  │   RAG Query  │  │   System     │  │   Health      │  │
│  │ CRUD API │  │   + Verify   │  │   Insights   │  │   Check       │  │
│  └────┬─────┘  └──────┬───────┘  └──────────────┘  └───────────────┘  │
│       │               │                                                │
│       ▼               ▼                                                │
│  ┌─────────────────────────────────────────────┐                       │
│  │         VeriRAG AI Engine (rag_logic.py)     │                       │
│  │                                             │                       │
│  │  ┌───────────┐    ┌──────────────────────┐  │                       │
│  │  │  Gemini   │───▶│  Critic Agent        │  │                       │
│  │  │ (Primary) │    │  (Faithfulness       │  │                       │
│  │  └───────────┘    │   Verification)      │  │                       │
│  │       │ failover  └──────────────────────┘  │                       │
│  │       ▼                                     │                       │
│  │  ┌───────────┐                              │                       │
│  │  │ Groq/     │                              │                       │
│  │  │ Llama-3   │                              │                       │
│  │  │ (Backup)  │                              │                       │
│  │  └───────────┘                              │                       │
│  └─────────────────────────────────────────────┘                       │
└──────┬──────────────┬──────────────┬──────────────┬────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  ┌─────────┐   ┌──────────┐  ┌──────────┐   ┌──────────┐
  │PostgreSQL│   │  Redis   │  │ Vault    │   │Prometheus│
  │+ pgvector│   │ (Broker) │  │ (Secrets)│   │+ Grafana │
  └─────────┘   └──────────┘  └──────────┘   └──────────┘
```

### Request Lifecycle

1. **User uploads a PDF** → Django saves it → Celery worker ingests it → LangChain chunks text → Google Embeddings → stored in **pgvector**
2. **User asks a question** → Similarity search in pgvector → **Gemini** generates answer → **Critic Agent** scores faithfulness
3. If faithfulness < `0.6` → answer is **rejected** → re-generated with **Groq/Llama-3** using a stricter prompt
4. Final response includes: answer, faithfulness score, source citations, and verification status

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19, Vite 7, Tailwind CSS | Bento Grid UI with glassmorphism aesthetic |
| **Backend** | Django 5.0, Django REST Framework | RESTful API with JWT authentication |
| **Primary LLM** | Google Gemini 1.5 Flash | Main response generation (JSON mode) |
| **Backup LLM** | Groq / Llama-3 8B | Automatic failover for hallucination recovery |
| **Vector DB** | PostgreSQL 16 + pgvector | Semantic similarity search on document embeddings |
| **Embeddings** | Google `text-embedding-004` | 768-dim vectors via LangChain |
| **Task Queue** | Celery + Redis 7 | Async document ingestion & scheduled tasks |
| **Secret Management** | HashiCorp Vault 1.13 | Dynamic API key retrieval with caching |
| **Observability** | Prometheus + Grafana | Custom metrics (hallucination rate, failovers, latency) |
| **Tracing** | OpenTelemetry | Distributed tracing across services |
| **Infrastructure** | Docker Compose / Kubernetes | Local dev + production-grade k8s manifests |
| **Cloud** | Azure (ACR, AKS, Terraform) | Container registry + orchestration |

---

## 🚀 Local Development Setup

### Prerequisites

- **Docker Desktop** (v4.x+) with Docker Compose
- **Git**
- **Google API Key** (for Gemini + Embeddings) — [Get one here](https://aistudio.google.com/app/apikey)
- **Groq API Key** (optional, for fallback LLM) — [Get one here](https://console.groq.com/)
- **Node.js 18+** and **npm** (for frontend development)

### Step 1: Clone & Configure

```bash
git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
cd cloud-native-ai-library-system
```

Create a `.env` file in the project root:

```env
# === Core Secrets ===
DJANGO_SECRET_KEY=your-random-secret-key-here
GOOGLE_API_KEY=AIza...your-google-api-key
GROQ_API_KEY=gsk_...your-groq-api-key

# === Database ===
POSTGRES_USER=admin
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=verirag_db
POSTGRES_HOST=rag-db
POSTGRES_PORT=5432

# === Redis ===
REDIS_URL=redis://rag-redis:6379/0

# === Vault ===
VAULT_ADDR=http://rag-vault:8200
VAULT_TOKEN=root

# === App Settings ===
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend,rag-backend
```

### Step 2: Start the Infrastructure

```bash
docker-compose up -d --build
```

This spins up **8 containers**: PostgreSQL (pgvector), Redis, Vault, Django backend, Celery worker, Celery beat, Prometheus, and Grafana.

### Step 3: Initialize HashiCorp Vault (Unseal Process)

Vault starts in **dev mode** by default with a root token of `root`. For production-like initialization:

```powershell
# Windows (PowerShell)
.\init_vault.ps1
```

**Manual Vault setup (cross-platform):**

```bash
# 1. Check vault status
docker exec rag-vault vault status

# 2. If sealed, unseal with your unseal key
docker exec rag-vault vault operator unseal <UNSEAL_KEY>

# 3. Authenticate with root token
docker exec rag-vault vault login root

# 4. Enable KV v2 secrets engine
docker exec rag-vault vault secrets enable -path=secret kv-v2

# 5. Store your API keys securely
docker exec rag-vault vault kv put secret/myapp \
  GOOGLE_API_KEY="AIza..." \
  GROQ_API_KEY="gsk_..."
```

> **Dev Mode:** When `VAULT_DEV_ROOT_TOKEN_ID=root` is set (default in docker-compose), Vault auto-initializes and unseals on startup. The `init_vault.ps1` script handles production initialization including key persistence to `vault_keys.txt`.

### Step 4: Run Database Migrations

```bash
docker exec -it rag-backend python manage.py migrate
docker exec -it rag-backend python manage.py createsuperuser
```

### Step 5: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` and the backend API at `http://localhost:8000`.

### Step 6: Verify Everything

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend Dashboard | http://localhost:5173 | Your superuser credentials |
| Django Admin | http://localhost:8000/admin/ | Superuser |
| Swagger API Docs | http://localhost:8000/api/schema/swagger-ui/ | JWT Token |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Vault UI | http://localhost:8200 | Token: `root` |

---

## 📁 Project Structure

```
cloud-native-ai-library-system/
├── backend/                    # Django REST API
│   ├── ai_engine/              # Core RAG + Verification engine
│   │   ├── rag_logic.py        # Dual-agent verification pipeline
│   │   ├── views.py            # API endpoints
│   │   ├── models.py           # Document model (multi-tenant)
│   │   ├── tasks.py            # Celery async tasks
│   │   ├── tracing.py          # OpenTelemetry integration
│   │   └── benchmarks.py       # Performance benchmarks
│   ├── rag_backend/            # Django project settings
│   │   ├── settings.py         # Production-grade config
│   │   ├── celery.py           # Celery app configuration
│   │   └── urls.py             # URL routing
│   ├── tests/                  # Pytest test suite
│   │   ├── conftest.py         # Shared fixtures (mocked Vault)
│   │   └── test_rag_logic.py   # RAG engine unit tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React + Vite + Tailwind CSS
│   ├── src/
│   │   ├── Dashboard.jsx       # Main library + AI chat (Bento Grid)
│   │   ├── Monitoring.jsx      # Mission Control telemetry
│   │   └── Analytics.jsx       # Query analytics dashboard
│   └── package.json
├── k8s/                        # Kubernetes manifests (GitOps-ready)
│   ├── namespace.yaml          # verirag namespace
│   ├── configmap.yaml          # Non-sensitive environment config
│   ├── secrets.yaml            # Base64-encoded secrets (template)
│   ├── deployment.yaml         # Backend, Celery, Redis deployments
│   ├── service.yaml            # ClusterIP + NodePort services
│   ├── statefulset.yaml        # PostgreSQL with persistent storage
│   └── kustomization.yaml      # Kustomize resource manager
├── infrastructure/             # Terraform (Azure ACR + AKS)
│   └── main.tf
├── docs/                       # Extended documentation
│   ├── ARCHITECTURE.md         # Dual-agent verification protocol
│   ├── API_SPEC.md             # REST API reference
│   └── SECURITY.md             # Vault + JWT + CSP security model
├── docker-compose.yml          # Local development orchestration
├── prometheus.yml              # Prometheus scrape configuration
└── init_vault.ps1              # Vault initialization script (Windows)
```

---

## 🧪 Testing

```bash
# Run backend tests with Pytest
cd backend
pytest tests/ -v --tb=short

# Run with coverage report
pytest tests/ --cov=ai_engine --cov-report=term-missing
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the dual-agent verification logic and [docs/API_SPEC.md](docs/API_SPEC.md) for complete API documentation.

---

## ☸️ Kubernetes Deployment

Production-grade Kubernetes manifests are in `k8s/`. Apply them with Kustomize:

```bash
# Apply all resources via Kustomize
kubectl apply -k k8s/

# Verify pods are running
kubectl get pods -n verirag

# Check services
kubectl get svc -n verirag

# View logs
kubectl logs -n verirag deployment/rag-backend --tail=50
```

For GitOps workflows, point Argo CD or Flux to the `k8s/` directory.

---

## 📊 Observability

- **Prometheus** scrapes custom metrics at `/metrics`:
  - `verirag_hallucination_rejections_total` — blocked hallucinations
  - `verirag_llm_fallbacks_total` — Gemini → Groq failovers
  - `verirag_queries_total` — total RAG queries
  - `verirag_documents_ingested_total` — processed documents
  - `verirag_faithfulness_score` — histogram of confidence scores
- **Grafana** dashboards visualize real-time AI integrity and infrastructure health
- **OpenTelemetry** provides distributed tracing across Django → Celery → pgvector

---

## 📄 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Dual-agent (Gemini + Llama-3/Groq) verification protocol |
| [API_SPEC.md](docs/API_SPEC.md) | Full REST API endpoint reference with request/response schemas |
| [SECURITY.md](docs/SECURITY.md) | HashiCorp Vault integration, JWT auth, CSP policies |

---

## 👥 Team 96 — The Azure-Native AI Librarian

Built for the Azure Cloud-Native hackathon.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
