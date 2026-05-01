# VeriRAG – Verified Research Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen)](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Node.js: 18+](https://img.shields.io/badge/Node.js-18%2B-green)](https://nodejs.org/)

---

## 🚀 What This Project Does

**VeriRAG** answers questions about your documents with **citations and confidence scores**. Unlike standard LLMs, every answer is verified for accuracy—if the system isn't confident, it refuses to answer.

**One-line value:** Trustworthy, citation-backed answers from your document library with built-in hallucination detection.

---

## 🧠 Why This Matters

### The Problem: Hallucination
Large language models confidently generate plausible-sounding answers that are completely false. When you ask GPT about your proprietary documents, it might invent details that never existed.

### The Solution: RAG + Verification
- **Retrieval**: Find relevant documents before answering
- **Augmentation**: Use those documents as evidence  
- **Verification**: Check if the answer is actually grounded in the evidence

If the confidence score drops below 0.6, VeriRAG rejects the answer rather than guess. This is production-grade reliability.

---

## ⚙️ How It Works (High Level)

```
User Query
    ↓
[1] RETRIEVE → Search vector database for relevant documents
    ↓
[2] RANK → Order by relevance + check confidence
    ↓
[3] GENERATE → Use configured Azure OpenAI model to synthesize answer from top chunks
    ↓
[4] VERIFY → Check if answer is grounded in source documents
    ↓
[5] RETURN/REJECT → Return answer with citations or refuse if uncertain
```

**No LLM involved until step [3].** Steps 1-2 are fast and deterministic.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  - Upload PDFs, ask questions, see citations                   │
│  - Command palette, intelligent search                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                 REST API (Django)
                       │
┌──────────────────────┴──────────────────────────────────────────┐
│                      BACKEND (Django 5.0)                       │
│  - RAG Pipeline: retrieve → rank → verify                      │
│  - Vector search & document management                          │
│  - Caching (Redis)                                             │
└──────────────┬───────────────────────────┬──────────────────────┘
               │                           │
    ┌──────────┴────────┐      ┌──────────┴──────────────┐
    │                   │      │                         │
┌───▼────────┐  ┌──────▼─┐   ┌┴───────┐        ┌─────────▼────┐
│ PostgreSQL │  │ pgvec  │   │ Redis  │        │ LLM API      │
│ (documents)│  │ (embs) │   │ (cache)│        │ - Azure OpenAI │
│            │  │        │   │        │        │ - Groq/Llama │
└────────────┘  └────────┘   └────────┘        └──────────────┘

     DEPLOYMENT: Docker → Azure Container Apps
     MONITORING: Prometheus + Grafana + Azure Monitor
```

---

## 🔥 Key Features

| Feature | What It Does |
|---------|-------------|
| **Citation Grounding** | Every answer includes source document references |
| **Hallucination Detection** | Scores each answer; rejects if confidence < 0.6 |
| **Grounded Generation** | Generates answers only from retrieved evidence |
| **PDF Ingestion** | Upload papers → automatic chunking → vector embedding |
| **Academic Search** | Query arXiv, Semantic Scholar, Patents within the platform |
| **Evaluation Metrics** | RAGAS scoring (faithfulness, relevancy, precision) |
| **Cost Optimized** | ~$97/month on Azure (scale-to-zero Container Apps) |
| **Observable** | Prometheus metrics, Grafana dashboards, tracing |

---

## 🧪 Demo Flow (Exact Script)

Run the demo locally:

```bash
docker-compose up --build
python demo_rag_test.py
```

**What happens:**

### Query 1: Valid, In-Domain
```
Q: "What is RAG?"
→ System retrieves definition documents
→ Generates answer: "RAG is Retrieval-Augmented Generation, which combines document retrieval with language models to generate grounded answers..."
→ Verification score: 0.94 ✅ PASS
→ Returns answer with citations
```

### Query 2: Valid, Synthesis Required
```
Q: "How does RAG reduce hallucination?"
→ System retrieves 3 related chunks (similarity: 0.75-0.88)
→ Calls LLM to synthesize comparison
→ Verification score: 0.87 ✅ PASS
→ Returns synthesized answer with source citations
```

### Query 3: Out-of-Domain (No Evidence)
```
Q: "Explain quantum computing in detail"
→ System retrieves documents (low relevance: 0.42)
→ Calls LLM to generate answer
→ Verification score: 0.31 ❌ FAIL (threshold is 0.6)
→ Returns: "I cannot answer this question with sufficient evidence from available documents."
```

**Why this matters:** Standard LLM would confidently explain quantum computing even if the documents don't cover it. VeriRAG refuses.

---

## 🛠 Local Setup

### Prerequisites
- Docker Desktop (Windows/Mac/Linux)
- API Keys:
  - Azure OpenAI resource with a deployed chat model

### Quick Start

1. **Clone & configure:**
   ```bash
   git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
   cd cloud-native-ai-library-system
   
   # Copy env template
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Start infrastructure (one command):**
   ```bash
   docker-compose up --build
   ```

3. **Create admin user:**
   ```bash
   docker exec rag-backend python manage.py createsuperuser
   ```

4. **Verify it works:**
   ```bash
   # Backend health check
   curl http://localhost:8000/api/health/
   
   # Frontend
   open http://localhost:5173
   ```

### Environment Variables (Required)
```env
DJANGO_SECRET_KEY=<your-secret>
AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
AZURE_OPENAI_API_KEY=<your-azure-openai-api-key>
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>
POSTGRES_HOST=rag-db
POSTGRES_DB=verirag_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=<password>
REDIS_URL=redis://rag-redis:6379/0
DEBUG=False  # Set to True only locally
FAITHFULNESS_THRESHOLD=0.6  # Min confidence to return answer
```

---

## ☁️ Deployment to Azure

VeriRAG is optimized for **Azure Container Apps** with Terraform IaC.

### Quick Deploy (5 minutes)
```bash
cd ops/infrastructure
terraform init
terraform apply -var-file=terraform.tfvars
```

### What gets deployed:
- **Backend**: Container App (scale 0-10 replicas)
- **Frontend**: Static Web App (CDN + global distribution)
- **Database**: PostgreSQL Flexible Server (B1S, ~$30/month)
- **Cache**: Redis (premium tier)
- **Monitoring**: Azure Monitor + Application Insights

**Cost:** ~$97/month including all databases.

See [docs/deployment.md](docs/deployment.md) for detailed Azure setup.

---

## 📊 Evaluation & Logging

VeriRAG tracks quality automatically.

### What Gets Logged
Every query records:
- **Retrieval metrics**: documents found, similarity scores
- **Generation metrics**: tokens used, LLM cost
- **Verification metrics**: faithfulness score, passed/rejected
- **RAGAS evaluation**: faithfulness, answer_relevancy, context_precision
- **Latency**: query to response time
- **Cost**: actual API costs per query

### Dashboard
Access metrics at:
```
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Azure Monitor: https://portal.azure.com
```

### Why It Matters
Track system reliability:
- Is verification working? (% queries rejected)
- Are responses improving? (faithfulness trend)
- What's the cost per query? (budget tracking)

See [docs/evaluation.md](docs/evaluation.md) for the complete evaluation framework.

---

## 📂 Project Structure

```
.
├── apps/
│   ├── backend/           # Django REST API
│   │   ├── ai_engine/     # RAG pipeline, faithfulness scoring
│   │   ├── rag_app/       # Document management, embeddings
│   │   └── rag_backend/   # Django settings
│   └── frontend/          # React + Vite
│       └── src/
│           ├── components/
│           └── pages/
│
├── ops/
│   ├── infrastructure/    # Terraform for Azure
│   ├── k8s/               # Kubernetes manifests (optional)
│   └── monitoring/        # Prometheus, Grafana configs
│
├── docs/                  # Technical documentation
│   ├── architecture.md
│   ├── rag_pipeline.md
│   ├── deployment.md
│   └── evaluation.md
│
├── tests/                 # Test suite
│   ├── test_faithfulness_scorer.py
│   └── test_rag_system.py
│
└── docker-compose.yml     # Local development stack
```

---

## ⚠️ Limitations & Assumptions

### What This System Does NOT Do
- **No live web search**: Only answers from uploaded documents
- **No fine-tuning**: Uses pretrained embeddings (Google's text-embedding-004)
- **No multi-language**: Optimized for English
- **No real-time collaboration**: Single-user or basic team access

### External Dependencies
- **Azure OpenAI**: Required for generation.
- **PostgreSQL + pgvector**: Must be running for vector search.
- **Embeddings**: Uses an Azure OpenAI embedding deployment.

### Known Constraints
- **Context window**: Limited to top-10 chunks (reduce for cost, increase for accuracy)
- **Verification threshold**: Fixed at 0.6 (tune higher for stricter, lower for permissive)
- **Latency**: LLM generation takes 1-3 seconds (depends on model)

---

## 🔮 Future Work

### Planned Enhancements
- **Hybrid Search**: Combine vector + keyword search (BM25)
- **Smart Chunking**: Semantic chunking instead of fixed 512-token chunks
- **Fine-tuning**: Custom embeddings on user's domain
- **Web Integration**: Augment local docs with web search results
- **Multi-agent Workflows**: Chain multiple RAG queries for complex questions

### Possible Improvements
- Streaming responses (WebSocket)
- Document version control
- Advanced RBAC (multi-user, team management)
- Structured data extraction
- Document relationship mapping

---

## 📚 Documentation

- **[Architecture](docs/architecture.md)** – System design, data flow, decision trees
- **[RAG Pipeline](docs/rag_pipeline.md)** – Three-tier retrieval strategy, scoring logic
- **[Deployment](docs/deployment.md)** – Azure setup, Terraform, monitoring
- **[Evaluation Framework](docs/evaluation.md)** – Testing methodology, metrics, RAGAS

---

## 🤝 Contributing

This is a research/production system. Contributions welcome:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Test your changes: `pytest tests/`
4. Submit a pull request

---

## 📜 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🆘 Support

- **Issues?** Open a GitHub issue with your error log
- **Questions?** See [docs/](docs/) for detailed guides
- **Local testing?** Run `python demo_rag_test.py`

---

**Last Updated:** April 2026 | **Status:** Production Ready ✅
