# VeriRAG - The Azure-Native AI Librarian

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active Development](https://img.shields.io/badge/status-active%20development-brightgreen)](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Node.js: 18+](https://img.shields.io/badge/Node.js-18%2B-green)](https://nodejs.org/)
[![Security: Policy](https://img.shields.io/badge/Security-Policy.md-blue)](.github/SECURITY.md)
[![Commits: Monthly](https://img.shields.io/badge/commits-28%2Fmonth-blueviolet)](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/commits)

> **A cloud-native RAG platform delivering trustworthy, citation-backed answers with dual-agent verification, academic research discovery, and automatic LLM failover.**

VeriRAG is an intelligent document library system that ingests PDFs and answers user questions with **verified, citation-backed responses**. The system scores each AI-generated answer for faithfulness and automatically regenerates responses using a backup LLM if verification fails. Includes dedicated **academic paper discovery** for PhD research with integration to Semantic Scholar, arXiv, and CrossRef.

---

## Key Features

- ✅ **Verified AI Responses** — Every answer is scored for faithfulness against source documents
- ✅ **Automatic Failover** — Regenerates responses using backup LLM if verification fails
- ✅ **Citation Grounding** — Provides source references for every answer
- ✅ **Academic Research Discovery** — Native integration with Semantic Scholar, arXiv, CrossRef, and Google Scholar for PhD research
- ✅ **OAuth Integration** — Google & GitHub authentication with social sign-in support
- ✅ **Cost Optimized** — Built for a $97/month budget on Azure
- ✅ **Production Ready** — Cloud-native architecture for Azure Container Apps
- ✅ **Observable** — Real-time metrics with Prometheus, Grafana, and Azure Monitor
- ✅ **Enhanced UX** — Command palette, intelligent search, and streamlined interface

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **Backend** | Django 5.0 + Django REST Framework |
| **Async Backend** | FastAPI (optional alternative for high-performance RAG) |
| **Primary LLM** | Google Gemini 1.5 Flash |
| **Backup LLM** | Groq / Llama-3 8B |
| **Academic Integration** | Semantic Scholar, arXiv, CrossRef, Google Scholar APIs |
| **Vector DB** | PostgreSQL 16 + pgvector |
| **Embeddings** | Google text-embedding-004 |
| **Task Queue** | Celery + Redis |
| **Cloud** | Azure Container Apps + ACR |
| **IaC** | Terraform |
| **Authentication** | OAuth 2.0 (Google & GitHub) |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Google API Key (Gemini + Embeddings) — [Get here](https://aistudio.google.com/app/apikey)
- Groq API Key (optional fallback) — [Get here](https://console.groq.com/)
- Node.js 18+ (frontend)
- (Optional) Google & GitHub OAuth credentials for social sign-in

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
   cd cloud-native-ai-library-system
   ```

2. **Create `.env` file:**
   ```env
   DJANGO_SECRET_KEY=your-secret-key
   GOOGLE_API_KEY=your-google-key
   GROQ_API_KEY=your-groq-key
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=devpassword
   POSTGRES_DB=verirag_db
   POSTGRES_HOST=rag-db
   POSTGRES_PORT=5432
   REDIS_URL=redis://rag-redis:6379/0
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend
   
   # OAuth (optional)
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-secret
   GITHUB_CLIENT_ID=your-github-client-id
   GITHUB_CLIENT_SECRET=your-github-secret
   ```

3. **Start infrastructure:**
   ```bash
   docker-compose up -d --build
   ```

4. **Run migrations:**
   ```bash
   docker exec -it rag-backend python manage.py migrate
   docker exec -it rag-backend python manage.py createsuperuser
   ```

5. **Start frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| API Docs | http://localhost:8000/api/schema/swagger-ui |

### OAuth Setup

See [Google & GitHub OAuth Setup Guide](docs/OAUTH_SETUP_GUIDE.md) for complete authentication configuration.

---

## Project Structure

```
cloud-native-ai-library-system/
├── apps/
│   ├── backend/                    # Django REST API
│   │   ├── ai_engine/              # RAG engine + verification
│   │   │   ├── rag_logic.py        # Core dual-agent pipeline
│   │   │   ├── academic_views.py   # Academic paper discovery & RAG
│   │   │   ├── auth_views.py       # OAuth & authentication endpoints
│   │   │   ├── views.py            # Core API endpoints
│   │   │   ├── models.py           # Database models (Papers, Users, etc.)
│   │   │   ├── tasks.py            # Celery async tasks
│   │   │   └── rag_logic.py        # Academic RAG pipeline
│   │   ├── mcp_server.py           # FastAPI RAG backend (optional)
│   │   └── requirements.txt
│   └── frontend/                   # React + Vite app
│       ├── src/
│       │   └── components/         # Command palette, search, auth UI
│       └── package.json
├── ops/
│   ├── infrastructure/             # Terraform (Azure)
│   └── k8s/                        # Kubernetes manifests
├── scripts/
│   ├── demo/                       # Demo scripts
│   ├── setup/                      # Setup & initialization scripts
│   └── testing/                    # Test scripts
├── docs/
│   ├── guides/                     # Deployment guides
│   ├── OAUTH_SETUP_GUIDE.md        # Google & GitHub OAuth setup
│   ├── ARCHITECTURE.md             # System design details
│   └── README.md                   # Detailed documentation
├── docker-compose.yml              # Local dev orchestration
└── README.md                        # This file
```

---

## Core Features

### Document RAG

Query your PDF library with verified, citation-backed answers:
```bash
curl -X POST http://localhost:8000/api/documents/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```

### Academic Research Discovery

Search and analyze academic papers across Semantic Scholar, arXiv, CrossRef:
```bash
curl -X POST http://localhost:8000/api/papers/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "source": "arxiv"}'
```

Features:
- 🔍 **Paper Search** — Query across multiple academic sources
- 📚 **Personal Library** — Organize and manage research papers
- 🔬 **Gap Analysis** — Identify research gaps and opportunities
- 💡 **Topic Recommendations** — Get smart topic suggestions based on your research
- ❓ **RAG Q&A** — Ask questions about papers with citation references

### Authentication & Authorization

- **Passwordless Email Login** — Sign in with email
- **OAuth 2.0 Social Sign-In** — Google & GitHub authentication
- **Secure Token Exchange** — Industry-standard OAuth flow

---

## Testing

```bash
cd apps/backend
pytest tests/ -v --tb=short
pytest tests/ --cov=ai_engine --cov-report=html
```

---

## Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -k ops/k8s/

# Verify pods
kubectl get pods -n verirag

# View logs
kubectl logs -n verirag deployment/rag-backend --tail=50
```

---

## AI Engine Documentation

Detailed documentation available in the `docs/` directory:
- **Deployment Guides** — `docs/guides/` for ACA, Kubernetes, and local setup
- **Architecture Details** — See `docs/guides/` for system design documentation
- **API Reference** — See backend Swagger docs at `/api/schema/swagger-ui/`
- **OAuth Setup** — [docs/OAUTH_SETUP_GUIDE.md](docs/OAUTH_SETUP_GUIDE.md)

---

## Recent Improvements

### Security & Infrastructure
- ✅ Trivy vulnerability scanning & remediation in CI/CD
- ✅ Latest patched base images (Python 3.12, Alpine 3.21)
- ✅ OIDC authentication for Azure Container Registry
- ✅ Consolidated CI/CD workflows (10 → 4 lean pipelines)

### Performance & Features
- ✅ Academic RAG system with multiple source integrations
- ✅ FastAPI backend alternative for high-performance scenarios
- ✅ Enhanced frontend UX with command palette
- ✅ Optimized local development environment
- ✅ Comprehensive budget & deployment guides

### Documentation
- ✅ OAuth setup guide for Google & GitHub
- ✅ Terraform budget optimization guide
- ✅ Local dev environment guide
- ✅ Cleaned up and consolidated documentation

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am "Add feature"`
4. Push to branch: `git push origin feature/your-feature`
5. Open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details

---

**Built for the Azure Cloud-Native Hackathon | Team 96
