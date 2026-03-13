# VeriRAG — Architecture Deep-Dive

> **Version 2.0 · March 2026**
> Azure-Native AI Library System with Dual-Agent Verification

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Service Topology](#3-service-topology)
4. [Security & Secret Management](#4-security--secret-management)
5. [The Dual-Agent AI Pipeline](#5-the-dual-agent-ai-pipeline)
6. [PDF Ingestion Flow](#6-pdf-ingestion-flow)
7. [RAG Query Flow](#7-rag-query-flow)
8. [Data Model](#8-data-model)
9. [Observability Stack](#9-observability-stack)
10. [Infrastructure Layers](#10-infrastructure-layers)
11. [Network & Port Map](#11-network--port-map)
12. [Failure Modes & Resilience](#12-failure-modes--resilience)

---

## 1. System Overview

VeriRAG is a **Retrieval-Augmented Generation (RAG)** system purpose-built for library document management. What separates it from vanilla RAG is the **Dual-Agent Verification Protocol**: every AI response is cross-checked by an independent "Critic Agent" before reaching the user, producing a quantitative **Faithfulness Score** that prevents hallucinations.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER (React SPA)                       │
│         Dashboard · Chat · Upload · Monitoring              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / JWT
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  DJANGO REST FRAMEWORK                       │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────┐  │
│  │ /api/docs/ │  │ /api/query │  │ /api/system-insights/ │  │
│  └─────┬──────┘  └─────┬──────┘  └───────────┬───────────┘  │
│        │               │                     │               │
│  ┌─────▼──────────────▼─────────────────────▼────────────┐  │
│  │              rag_logic.py (AI Engine)                   │  │
│  │  ┌──────────────┐   ┌───────────────┐                  │  │
│  │  │ Generator    │──▶│ Critic Agent  │ ◀─ Faithfulness  │  │
│  │  │ (Gemini 1.5) │   │ (Groq/Llama3) │   Verification   │  │
│  │  └──────┬───────┘   └───────────────┘                  │  │
│  │         │                                               │  │
│  │  ┌──────▼───────┐  ┌────────────┐  ┌──────────────┐   │  │
│  │  │ PGVector     │  │ Redis      │  │ HashiCorp    │   │  │
│  │  │ (Embeddings) │  │ (Celery)   │  │ Vault (Keys) │   │  │
│  │  └──────────────┘  └────────────┘  └──────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + Vite 7 | SPA with Bento Grid dashboard |
| **UI Framework** | Tailwind CSS 3 + shadcn/ui | Dark-mode glass-morphism components |
| **Icons** | Lucide React | Consistent icon set |
| **Backend** | Python 3.11+, Django 5.0, DRF | REST API, Auth, ORM |
| **Auth** | SimpleJWT | Stateless JWT authentication |
| **Generator LLM** | Google Gemini 1.5 Flash | Primary RAG answer generation via `google.genai` SDK |
| **Critic LLM** | Llama-3 8B (Groq) | Faithfulness verification via OpenAI-compatible API |
| **Vector Store** | PostgreSQL 16 + pgvector | Embedding storage & similarity search |
| **Task Queue** | Celery + Celery Beat | Async PDF ingestion, scheduled maintenance |
| **Message Broker** | Redis 7 Alpine | Celery broker + result backend |
| **Secret Manager** | HashiCorp Vault 1.13 (KV v2) | Runtime API key retrieval |
| **Metrics** | Prometheus + django-prometheus | Custom counters, histograms, gauges |
| **Dashboards** | Grafana 10 | Visual metrics display |
| **Tracing** | OpenTelemetry (optional) | Distributed tracing across pipeline |
| **Containerization** | Docker Compose (dev) | Local development orchestration |
| **Target Infra** | Azure Kubernetes Service (AKS) | Production deployment target |

---

## 3. Service Topology

All services run on a single Docker bridge network (`rag-network`):

```
┌─────────────────── Docker Compose Cluster ───────────────────┐
│                                                               │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐             │
│  │ rag-vault│     │ rag-db   │     │ rag-redis│             │
│  │ :8200    │     │ :5432    │     │ :6379    │             │
│  │ Vault    │     │ PG+pgvec │     │ Redis 7  │             │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘             │
│       │                │                │                     │
│  ┌────▼────────────────▼────────────────▼──────┐             │
│  │              rag-backend (:8000)             │             │
│  │         Django + DRF + rag_logic.py          │             │
│  └──────────────────┬──────────────────────────┘             │
│                     │                                         │
│       ┌─────────────┼─────────────┐                          │
│  ┌────▼─────┐  ┌────▼─────┐  ┌───▼────────┐                │
│  │celery-   │  │ celery-  │  │ rag-       │                │
│  │worker    │  │ beat     │  │ prometheus │                │
│  │(ingestion│  │(schedule)│  │ :9090      │                │
│  └──────────┘  └──────────┘  └─────┬──────┘                │
│                                     │                        │
│                              ┌──────▼──────┐                │
│                              │ rag-grafana │                │
│                              │ :3000       │                │
│                              └─────────────┘                │
│                                                               │
│  ┌──────────┐                                                │
│  │ rag-mongo│  (Optional — future audit logs)                │
│  │ :27017   │                                                │
│  └──────────┘                                                │
└───────────────────────────────────────────────────────────────┘
```

---

## 4. Security & Secret Management

### 4.1 The Golden Rule

> **STRICT RULE**: API keys (`GOOGLE_API_KEY`, `GROQ_API_KEY`) NEVER appear in:
> - `.env` files
> - Django `settings.py`
> - React source code
> - `docker-compose.yml` environment blocks
> - Git history

### 4.2 How Secrets Flow

```
Developer                    Vault (rag-vault:8200)              Django / Celery
─────────                    ──────────────────────              ───────────────
   │                                │                                  │
   │  1. Run scripts/setup/init_vault.ps1 │                           │
   │  ─────────────────────────────▶│                                  │
   │     (enter GOOGLE_API_KEY &    │                                  │
   │      GROQ_API_KEY interactively│                                  │
   │                                │                                  │
   │  2. Keys stored at:            │                                  │
   │     secret/data/myapp          │                                  │
   │     ┌─────────────────────┐    │                                  │
   │     │ GOOGLE_API_KEY: ... │    │                                  │
   │     │ GROQ_API_KEY:  ... │    │                                  │
   │     └─────────────────────┘    │                                  │
   │                                │                                  │
   │                                │  3. On every API call,           │
   │                                │◀──── rag_logic.py calls          │
   │                                │      get_api_key_from_vault()    │
   │                                │                                  │
   │                                │  4. Returns key (cached 5 min)  │
   │                                │────────────────────────────────▶│
   │                                │                                  │
   │                                │  5. If Vault sealed/down,       │
   │                                │     falls back to env vars      │
   │                                │     (for dev only)               │
```

### 4.3 What `.env` Contains (Only)

```env
VAULT_ADDR=http://rag-vault:8200   # Where to find Vault
VAULT_TOKEN=root                   # Dev token — rotate in prod

POSTGRES_HOST=rag-db               # Infrastructure addresses
POSTGRES_DB=verirag_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=devpassword      # Move to Vault in production

REDIS_URL=redis://rag-redis:6379/0
DJANGO_SECRET_KEY=...
```

### 4.4 Vault Integration Code Path

```
rag_logic.py
├── _get_vault_client()          → Creates authenticated hvac.Client
├── get_api_key_from_vault()     → KV v2 read with per-key caching
│   ├── Cache hit?  → return immediately
│   ├── Vault up?   → read secret/myapp, cache result
│   └── Vault down? → fallback to os.environ.get()
├── get_groq_api_key()           → Shorthand for Groq key retrieval
└── get_embedding_model()        → GoogleGenerativeAIEmbeddings with Vault key
```

### 4.5 Celery Worker Vault Access

All Celery containers now receive `VAULT_ADDR` and `VAULT_TOKEN` via `docker-compose.yml`, enabling workers to call `get_api_key_from_vault()` during document ingestion without crashing.

---

## 5. The Dual-Agent AI Pipeline

VeriRAG uses a **Generator → Critic** architecture inspired by constitutional AI:

```
                  ┌─────────────────────────────────────┐
                  │        GENERATOR AGENT               │
                  │   Google Gemini 1.5 Flash             │
                  │                                       │
                  │   • Temperature: 0.1 (factual)       │
                  │   • Response format: JSON             │
                  │   • Constrained to context only       │
                  └──────────────┬────────────────────────┘
                                 │
                          Answer + Self-Score
                                 │
                                 ▼
                  ┌─────────────────────────────────────┐
                  │         CRITIC AGENT                  │
                  │   Groq Llama-3 8B                     │
                  │                                       │
                  │   • verify_faithfulness()             │
                  │   • Term overlap analysis             │
                  │   • Novelty penalty calculation       │
                  │   • Combined score = 60% LLM +       │
                  │     40% algorithmic verification      │
                  └──────────────┬────────────────────────┘
                                 │
                        Faithfulness Score
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              Score ≥ 0.6               Score < 0.6
              (PASS ✅)                (FAIL ❌)
                    │                         │
                    ▼                         ▼
             Return answer        Regenerate with stricter
             to user              prompt via Groq/Llama-3
                                  (verification protocol)
```

### 5.1 Failover Logic

```python
call_llm_with_fallback(prompt, api_key):
    try:
        response = call_gemini(prompt, api_key)    # Primary
        return response, "gemini"
    except:
        ACTIVE_MODEL.set(2)                         # Prometheus gauge
        LLM_FALLBACKS.inc()                         # Counter
        response = call_groq_llama(prompt)          # Backup
        return response, "groq"
```

If **both** LLMs fail, the system returns a graceful error JSON with `"model_used": "error"` — it never crashes.

---

## 6. PDF Ingestion Flow

```
User uploads PDF via React UI
        │
        ▼
[POST /api/documents/]  ──▶  DocumentViewSet.perform_create()
        │
        ▼
  Django saves file to media/documents/
  Creates Document model (processed=False)
        │
        ▼
  ingest_document(doc_id) called synchronously
        │
        ├── 1. PyPDFLoader extracts raw text (per page)
        │
        ├── 2. RecursiveCharacterTextSplitter
        │      chunk_size=1000, overlap=200
        │      separators: ["\n\n", "\n", ". ", " ", ""]
        │
        ├── 3. Metadata enrichment
        │      user_id, document_id, document_title, chunk_index
        │
        ├── 4. GoogleGenerativeAIEmbeddings (text-embedding-004)
        │      API key fetched from Vault
        │
        ├── 5. PGVector.from_documents()
        │      Stores embeddings in PostgreSQL
        │
        ├── 6. Document.processed = True
        │
        └── 7. DOCUMENTS_INGESTED.inc() (Prometheus)
```

### Celery Background Processing

For scheduled batch processing, Celery Beat triggers `process_pending_documents` every 5 minutes, queuing `ingest_document_task` for up to 10 unprocessed documents per cycle. Each task retries up to 3 times with exponential backoff.

---

## 7. RAG Query Flow

```
User types question in VeriRAG chat
        │
        ▼
[POST /api/query/]  ──▶  query_llm() view
        │
        ▼
  get_verified_answer(query, user_id)
        │
        ├── 1. QUERIES_TOTAL.inc()
        │
        ├── 2. get_api_key_from_vault("GOOGLE_API_KEY")
        │      └── Vault → cache → env fallback
        │
        ├── 3. PGVector similarity_search(query, k=5)
        │      └── filter: { user_id: <current_user> }
        │      └── Multi-tenant isolation enforced
        │
        ├── 4. Build context from top-5 chunks
        │      └── Include source citations per chunk
        │
        ├── 5. call_llm_with_fallback(generation_prompt)
        │      ├── Try Gemini 1.5 Flash (JSON mode)
        │      └── Fallback to Groq/Llama-3
        │
        ├── 6. Parse JSON response
        │
        ├── 7. verify_faithfulness(answer, context, query)
        │      ├── Term overlap analysis
        │      ├── Novelty penalty calculation
        │      └── Combined score = 60% LLM + 40% algo
        │
        ├── 8. FAITHFULNESS_HISTOGRAM.observe(score)
        │
        ├── 9. If score < 0.6:
        │      ├── VERIFICATION_REJECTIONS.inc()
        │      └── Regenerate with strict prompt via Groq
        │
        └── 10. Return standardized JSON response
              {
                answer, faithfulness_score, explanation,
                source_citation, verification_passed,
                model_used, context_chunks_used
              }
```

---

## 8. Data Model

```
┌──────────────────────────────┐
│         Document             │
├──────────────────────────────┤
│ id          : BigAutoField   │
│ title       : CharField      │
│ file        : FileField      │
│ uploaded_at : DateTimeField  │
│ processed   : BooleanField   │
│ user        : ForeignKey     │──▶ auth.User
└──────────────────────────────┘

┌──────────────────────────────────┐
│  PGVector Collection             │
│  (langchain_pg_collection)       │
├──────────────────────────────────┤
│ name: "rag_collection"          │
│ cmetadata: { user_id,           │
│   document_id, document_title,  │
│   chunk_index, page, source }   │
│ embedding: vector(768)          │
│ document: text                  │
└──────────────────────────────────┘
```

---

## 9. Observability Stack

### 9.1 Custom Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `verirag_hallucination_rejections_total` | Counter | Responses rejected for low faithfulness |
| `verirag_llm_fallbacks_total` | Counter | Gemini → Groq failover events |
| `verirag_queries_total` | Counter | Total RAG queries processed |
| `verirag_documents_ingested_total` | Counter | Documents successfully indexed |
| `verirag_faithfulness_score` | Histogram | Distribution of faithfulness scores |
| `verirag_active_model` | Gauge | Active LLM (1=Gemini, 2=Groq) |

### 9.2 Health Endpoint

`GET /api/health/` — Public, no auth required. Checks:
- **PostgreSQL**: `SELECT 1` with latency measurement
- **Redis**: `ping()` with latency measurement
- **Vault**: `read_seal_status()` with latency measurement

Returns `200 OK` if all healthy, `503` if degraded.

### 9.3 Pipeline

```
Django ──(django-prometheus)──▶ /metrics endpoint
                                      │
                               Prometheus scrapes
                               every 15s
                                      │
                                      ▼
                              Grafana dashboards
                              (localhost:3000)
```

---

## 10. Infrastructure Layers

### 10.1 Local Development (Current)

Docker Compose with 9 services on `rag-network` bridge network.

### 10.2 Production Target — Azure Kubernetes Service (AKS)

```
┌─────────────────── AKS Cluster ────────────────────────┐
│                                                         │
│  Namespace: verirag                                     │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Deployments                                  │       │
│  │  • verirag-backend (2 replicas)             │       │
│  │  • verirag-celery-worker (2 replicas)       │       │
│  │  • verirag-celery-beat (1 replica)          │       │
│  │  • verirag-frontend (2 replicas, nginx)     │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ StatefulSets                                 │       │
│  │  • postgresql (PVC for data persistence)    │       │
│  │  • redis (PVC for AOF persistence)          │       │
│  │  • vault (PVC for storage backend)          │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Services                                     │       │
│  │  • verirag-backend (ClusterIP :8000)         │       │
│  │  • verirag-frontend (LoadBalancer :80/443)   │       │
│  │  • postgresql (ClusterIP :5432)              │       │
│  │  • redis (ClusterIP :6379)                   │       │
│  │  • vault (ClusterIP :8200)                   │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ConfigMaps: env vars, prometheus.yml                   │
│  Secrets: VAULT_TOKEN, DJANGO_SECRET_KEY               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 11. Network & Port Map

| Service | Container | Internal Port | External Port | Protocol |
|---------|-----------|---------------|---------------|----------|
| React Frontend | (Vite dev) | 5173 | 5173 | HTTP |
| Django API | rag-backend | 8000 | 8000 | HTTP |
| PostgreSQL | rag-db | 5432 | 5432 | TCP |
| Redis | rag-redis | 6379 | 6379 | TCP |
| Vault | rag-vault | 8200 | 8200 | HTTP |
| Prometheus | rag-prometheus | 9090 | 9090 | HTTP |
| Grafana | rag-grafana | 3000 | 3000 | HTTP |
| MongoDB | rag-mongo | 27017 | 27017 | TCP |

---

## 12. Failure Modes & Resilience

| Failure | Impact | Mitigation |
|---------|--------|------------|
| **Vault sealed** | Cannot fetch API keys | Graceful fallback to env vars; health endpoint reports "sealed" |
| **Vault unreachable** | Same as sealed | 5-minute cache prevents cascading failures; env fallback |
| **Gemini API down** | Primary LLM offline | Automatic failover to Groq/Llama-3; `LLM_FALLBACKS` counter incremented |
| **Groq API down** | Backup LLM offline | Returns structured error JSON; never crashes |
| **Both LLMs down** | No AI responses | User sees "All AI providers unavailable" with `model_used: "error"` |
| **PostgreSQL down** | No data access | Health endpoint returns 503; Django connection retry |
| **Redis down** | Celery stops | Tasks queue on restart; health endpoint flags it |
| **Low faithfulness** | Potential hallucination | Score < 0.6 triggers re-generation via Critic Agent with stricter prompt |
| **PDF extraction fails** | Document not indexed | `ingest_document_task` retries 3x with exponential backoff |

---

*Architecture maintained by Team 96 — VeriRAG Project*
