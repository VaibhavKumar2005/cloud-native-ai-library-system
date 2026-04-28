# VeriRAG Architecture

## System Overview

VeriRAG is a **three-tier retrieval system** optimized for accuracy and cost. The architecture prioritizes accuracy through verification while maintaining sub-2-second response times.

```
Query → [Cache] → [Embed] → [Vector Search] → [Verify] → Response
  ↓                                              ↓
10ms ← ← ← ← ← ← ← ← ← ← ← ← [LLM Synthesis]
(hit)                            (if needed)
```

---

## Core Components

### 1. Frontend (React + Vite)
- **Purpose**: Document upload, query interface, result visualization
- **Tech**: React 19, Tailwind CSS, axios
- **Features**:
  - PDF upload with progress tracking
  - Query input with search history
  - Citation highlighting
  - Confidence score display
  - Academic paper search integration

### 2. Backend API (Django REST Framework)
- **Purpose**: RAG orchestration, authentication, data management
- **Tech**: Django 5.0, Gunicorn, PostgreSQL
- **Endpoints**:
  - `POST /api/query/` → Submit question
  - `POST /api/documents/upload/` → Upload PDFs
  - `GET /api/documents/` → List uploaded docs
  - `GET /api/evaluation/` → View metrics

### 3. Vector Store (PostgreSQL + pgvector)
- **Purpose**: Semantic search via embeddings
- **Tech**: PostgreSQL 16 with pgvector extension
- **Data Model**:
  ```sql
  documents (id, title, source, upload_date, user_id)
  chunks (id, document_id, page_no, content, embedding, metadata)
  ```
- **Indexing**: HNSW (Hierarchical Navigable Small Worlds)
- **Query**: `SELECT * FROM chunks ORDER BY embedding <-> query_embedding LIMIT 10`

### 4. LLM APIs
- **Primary**: Google Gemini 1.5 Flash
  - Cost: $0.075/1M input tokens, $0.30/1M output
  - Speed: ~1-2 seconds per query
  - Fallback: Groq Llama-3 8B ($0.59/1M tokens)
  
### 5. Embeddings Model
- **Model**: Google text-embedding-004 (512-dim)
- **Cost**: $0.00006 per 1K tokens
- **Used for**: Query and document embedding, similarity search

### 6. Cache Layer (Redis)
- **Purpose**: Store query results (50% cache hit rate expected)
- **TTL**: 24 hours
- **Keys**: Hash of query (MD5)
- **Benefit**: <10ms response, $0 cost for cache hits

### 7. Monitoring (Prometheus + Grafana)
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Azure Monitor**: Production metrics (optional)

---

## Data Flow

### Request Flow
```
1. User Query
   ↓
2. Authentication (OAuth or session)
   ↓
3. Query Embedding (Google API, 0.00006 cost)
   ↓
4. Vector Search (pgvector, <50ms)
   - Retrieves top 10 chunks by cosine similarity
   ↓
5. Confidence Decision
   - High confidence (≥0.88): Return directly
   - Medium confidence (0.70-0.88): Call LLM to synthesize
   - Low confidence (<0.70): Reject
   ↓
6. Verification (Faithfulness scoring)
   - Semantic verification (embedding similarity)
   - RAGAS evaluation (optional, more comprehensive)
   ↓
7. Response Formatting
   - Answer + citations + confidence score
   ↓
8. Caching (Redis)
   - Store for 24 hours
   ↓
9. Return to Frontend
```

### Document Ingestion Flow
```
1. User uploads PDF
   ↓
2. Extract text (PyPDF2)
   ↓
3. Chunk text (512 tokens, 50% overlap)
   ↓
4. Embed chunks (Google API)
   ↓
5. Store in pgvector
   ↓
6. Update metadata (title, source, upload date)
```

---

## Three-Tier Retrieval Strategy

### Tier 1: Direct Retrieval (~70% of queries)
**Condition**: Similarity score ≥ 0.88 AND chunk is Q&A formatted

**Process**:
1. Vector search finds exact match
2. Return chunk directly (no LLM call)
3. Format with citations

**Cost**: $0.00006 (embedding only)  
**Latency**: <50ms  
**Example**:
```
Q: "What is semantic chunking?"
→ Vector DB returns chunk (sim: 0.94)
→ Return directly with BibTeX citation
```

### Tier 2: LLM Synthesis (~25% of queries)
**Condition**: Similarity score between 0.70-0.88

**Process**:
1. Vector search returns 3-5 relevant chunks
2. Call LLM to synthesize into coherent answer
3. Attach citations from all chunks
4. Verify faithfulness

**Cost**: $0.0005 (LLM call)  
**Latency**: 1-3 seconds  
**Example**:
```
Q: "Compare vector databases"
→ Vector DB returns 3 chunks (sim: 0.75, 0.73, 0.71)
→ LLM synthesizes comparison
→ Verify against chunks
```

### Tier 3: Graceful Rejection (~5% of queries)
**Condition**: Similarity score < 0.70

**Process**:
1. System determines insufficient evidence
2. Return rejection message
3. Suggest related topics (if available)

**Cost**: $0  
**Latency**: <100ms  
**Example**:
```
Q: "Explain GraphRAG" (not in docs)
→ Vector search finds low-relevance chunks
→ System refuses to answer
→ Returns: "No sufficient evidence in available documents"
```

---

## Faithfulness Verification Pipeline

### Semantic Verification (Fast)
**Method**: Embedding cosine similarity

```
Step 1: Embed answer
Step 2: Embed context chunks
Step 3: Calculate cosine similarity
Step 4: Compare against threshold (0.6)
```

**Advantages**:
- <50ms execution time
- No additional API calls
- Catches obvious hallucinations

**Limitations**:
- Only detects semantic drift
- May miss subtle factual errors

### RAGAS Evaluation (Comprehensive)
**Method**: LLM-based quality assessment using domain-specific metrics

**Metrics** (weighted):
- **Faithfulness** (50%): Is answer grounded in context?
- **Answer Relevancy** (30%): Does answer address the question?
- **Context Precision** (20%): Are retrieved chunks relevant?
- **Context Recall** (0% in practice): Did we retrieve enough? (requires ground truth)

**Example Scores**:
```
High-quality answer (should pass):
  faithfulness: 0.95
  answer_relevancy: 0.92
  context_precision: 0.88
  → combined_score: 0.92 ✅ PASS (≥0.6)

Low-quality answer (should reject):
  faithfulness: 0.35 (hallucination)
  answer_relevancy: 0.85
  context_precision: 0.80
  → combined_score: 0.52 ❌ FAIL (<0.6)
```

**Cost**: Depends on LLM (small prompt, fast)  
**Latency**: 1-2 seconds additional  
**Fallback**: If RAGAS library unavailable, use semantic verification

---

## Decision Tree (Real Example)

```
Query: "What is semantic chunking?"
├─ Hash Check
│  └─ Cache hit? NO
│
├─ Embedding
│  └─ Cost: $0.00006
│
├─ Vector Search (pgvector)
│  ├─ Top result: similarity = 0.94
│  ├─ Tier 1 Decision: 0.94 ≥ 0.88? YES
│  └─ Score: HIGH CONFIDENCE
│
├─ Response Path: DIRECT RETRIEVAL
│  ├─ Return: "Semantic chunking divides documents based on meaning..."
│  ├─ Citation: "[1] Langchain Docs, page 42"
│  └─ Confidence: 0.94
│
├─ Verification
│  ├─ Semantic score: 0.92
│  ├─ RAGAS faithfulness: 0.96
│  ├─ Combined: 0.94 ✅ PASS
│  └─ Method used: DIRECT (no LLM)
│
├─ Caching
│  └─ Stored in Redis for 24h
│
└─ Return (Latency: 45ms, Cost: $0.00006)
```

---

## Cost Model

### Per-Query Breakdown (Average)

| Step | Cost | Notes |
|------|------|-------|
| Embedding | $0.00006 | 100% of queries |
| Vector search | $0 | Runs in-database |
| Cache hit (50%) | $0 | <10ms response |
| LLM synthesis (25%) | $0.0005 | Only when needed |
| RAGAS eval (optional) | $0.0001 | Comprehensive verification |
| **Total (avg)** | **$0.00019** | ~$0.19 per 1000 queries |

### Monthly Cost Example
```
1,000 queries/day (30 queries/user * 30 users)
= 30,000 queries/month

Cost breakdown:
- Embeddings: 30,000 × $0.00006 = $1.80
- LLM synthesis (25%): 7,500 × $0.0005 = $3.75
- RAGAS eval (10%): 3,000 × $0.0001 = $0.30
- PostgreSQL (B1S): ~$30
- Redis (premium): ~$15
- Container Apps (2 vCPU, 4GB): ~$40
- ─────────────────────────────
Total: ~$91/month
```

---

## Scaling Considerations

### Current Limits (Single Instance)
- **QPS**: ~20 queries/second
- **Concurrent connections**: 100
- **Vector DB**: 1M documents (~100GB)

### Scaling Strategy
```
Load increases?
  ↓
[1] Redis cache hit rate improves → free scaling
[2] Container Apps auto-scales (0-10 replicas)
[3] PostgreSQL read replicas for embeddings
[4] Sharding strategy: By document source or user
```

### Kubernetes Support
Optional `ops/k8s/` contains manifests for cluster deployment:
- Horizontal pod autoscaling
- Service mesh (Istio optional)
- Persistent volumes for pgvector
- Distributed caching (Redis Cluster)

---

## Security

### Authentication
- OAuth 2.0 (Google, GitHub)
- Session tokens stored in httponly cookies
- CSRF protection

### Data Protection
- Encryption at rest (Azure Storage)
- Encryption in transit (TLS 1.3)
- Secrets management via Azure Key Vault

### API Security
- Rate limiting: 100 req/min per user
- Input validation (query length <500 chars)
- SQL injection protection via ORM

---

## Monitoring & Observability

### Key Metrics
```
verirag_queries_total                 # Total queries
verirag_verification_rejections       # Hallucinations prevented
verirag_faithfulness_score            # Avg verification score
verirag_response_latency_seconds      # Query-to-response time
verirag_embedding_cost_usd            # Daily API costs
```

### Traces
- OpenTelemetry integration
- Trace ID propagation
- Span attributes: query, model, cost, verification result

### Alerts
- Verification rejection rate > 20%
- Average latency > 5 seconds
- Daily cost > budget threshold
- Redis cache miss rate > 70%

---

## Assumptions & Design Decisions

| Decision | Why |
|----------|-----|
| pgvector over Pinecone | Self-hosted cost savings, simpler ops |
| Google Gemini over GPT-4 | Token cost 10x cheaper, sufficient quality |
| Fixed threshold (0.6) | Optimized for RAG demo use case |
| 512-token chunks | Balance: granular retrieval vs. context loss |
| 50% cache hit rate | Conservative estimate, actual: 40-60% |
| No fine-tuning | Cost/benefit not justified at small scale |

---

See also: [RAG Pipeline Deep Dive](rag_pipeline.md), [Deployment Guide](deployment.md)
