# VeriRAG - The Azure-Native AI Librarian

> **A cloud-native RAG platform delivering trustworthy, citation-backed answers with dual-agent verification and automatic LLM failover.**

VeriRAG is an intelligent document library system that ingests PDFs and answers user questions with **verified, citation-backed responses**. The system scores each AI-generated answer for faithfulness and automatically regenerates responses using a backup LLM if verification fails.

---

## Key Features

- ✅ **Verified AI Responses** — Every answer is scored for faithfulness against source documents
- ✅ **Automatic Failover** — Regenerates responses using backup LLM if verification fails
- ✅ **Citation Grounding** — Provides source references for every answer
- ✅ **Cost Optimized** — Built for a $97/month budget on Azure
- ✅ **Production Ready** — Cloud-native architecture for Azure Container Apps
- ✅ **Observable** — Real-time metrics with Prometheus, Grafana, and Azure Monitor

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **Backend** | Django 5.0 + Django REST Framework |
| **Primary LLM** | Google Gemini 1.5 Flash |
| **Backup LLM** | Groq / Llama-3 8B |
| **Vector DB** | PostgreSQL 16 + pgvector |
| **Embeddings** | Google text-embedding-004 |
| **Task Queue** | Celery + Redis |
| **Cloud** | Azure Container Apps + ACR |
| **IaC** | Terraform |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Google API Key (Gemini + Embeddings) — [Get here](https://aistudio.google.com/app/apikey)
- Groq API Key (optional fallback) — [Get here](https://console.groq.com/)
- Node.js 18+ (frontend)

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

---

## Project Structure

```
cloud-native-ai-library-system/
├── apps/
│   ├── backend/                    # Django REST API
│   │   ├── ai_engine/              # RAG engine + verification
│   │   │   ├── rag_logic.py        # Core dual-agent pipeline
│   │   │   ├── views.py            # API endpoints
│   │   │   ├── models.py           # Database models
│   │   │   └── tasks.py            # Celery async tasks
│   │   └── requirements.txt
│   └── frontend/                   # React + Vite app
├── ops/
│   ├── infrastructure/             # Terraform (Azure)
│   └── k8s/                        # Kubernetes manifests
├── scripts/
│   ├── demo/                       # Demo scripts
│   ├── setup/                      # Setup scripts
│   └── testing/                    # Test scripts
├── docs/
│   └── guides/                     # Deployment & setup guides
├── docker-compose.yml              # Local dev orchestration
└── README.md                        # This file
```

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
