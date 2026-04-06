# 🏗️ VeriRAG Architecture — Dual-Agent Verification Protocol

## Overview

VeriRAG implements a **dual-agent verification architecture** that prevents AI hallucinations in document Q&A. Instead of trusting a single LLM's output, every response passes through a multi-stage verification pipeline that combines two independent language models with heuristic analysis.

---

## System Architecture Diagram

```
                    ┌─────────────────────┐
                    │     User Query      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  JWT Authentication │
                    │  (SimpleJWT)        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  query_llm()        │
                    │  views.py           │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │     get_verified_answer()        │
              │     rag_logic.py                 │
              └────────────────┬────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Step 1: Context │  │ Step 2: Generate │  │ Step 3: Verify  │
│ Retrieval       │  │ Response         │  │ Faithfulness    │
│ (pgvector)      │  │ (Gemini)         │  │ (Critic Agent)  │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                     │                     │
         │                     │           ┌─────────▼─────────┐
         │                     │           │ Score < 0.6?       │
         │                     │           │ ┌───┐    ┌────┐   │
         │                     │           │ │YES│    │ NO │   │
         │                     │           │ └─┬─┘    └──┬─┘   │
         │                     │           └───┼─────────┼─────┘
         │                     │               │         │
         │                     │     ┌─────────▼───┐     │
         │                     │     │ Step 4:     │     │
         │                     │     │ Regenerate  │     │
         │                     │     │ (Groq/      │     │
         │                     │     │  Llama-3)   │     │
         │                     │     └─────────┬───┘     │
         │                     │               │         │
         └─────────────────────┴───────────────┴────┬────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │  Standardized JSON  │
                                         │  Response           │
                                         └─────────────────────┘
```

---

## The Five-Stage Verification Pipeline

### Stage 1: Context Retrieval (pgvector Similarity Search)

When a user submits a query, the system performs a **cosine similarity search** against the pgvector database to retrieve the top-5 most relevant document chunks.

**Key details:**
- **Embedding Model:** Google `text-embedding-004` (768 dimensions)
- **Vector Store:** PostgreSQL 16 + pgvector extension via LangChain's `PGVector` class
- **Multi-tenant isolation:** Chunks are filtered by `user_id` metadata, ensuring users only query their own documents
- **Chunk strategy:** `RecursiveCharacterTextSplitter` with 1000-char chunks and 200-char overlap

```python
# Similarity search with user isolation
docs = vector_db.similarity_search(
    query, k=5,
    filter={"user_id": str(user_id)}
)
```

Each retrieved chunk includes metadata: source document title, page number, chunk index, and user ID.

---

### Stage 2: Primary Response Generation (Gemini Agent)

The retrieved context chunks are formatted into a structured prompt and sent to **Google Gemini 1.5 Flash** with strict instructions:

- **Temperature:** 0.1 (near-deterministic for factual accuracy)
- **Response format:** `application/json` (enforced JSON mode)
- **System prompt:** Instructs the model to ONLY use information from the provided context
- **Output schema:** `answer`, `faithfulness_score`, `explanation`, `source_citation`

```python
generation_config = {
    "temperature": 0.1,
    "response_mime_type": "application/json"
}
model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
```

The model self-reports a `faithfulness_score` (0.0–1.0) indicating its confidence that the answer is fully grounded in the context.

---

### Stage 3: Critic Agent — Faithfulness Verification

The Critic Agent performs **second-pass verification** using heuristic analysis independent of the LLM's self-assessment. This is the core innovation of VeriRAG.

**Verification algorithm (`verify_faithfulness()`):**

1. **Term Overlap Analysis:** Extracts all words (≥4 chars) from both the answer and the context. Calculates the ratio of answer terms that appear in the context.

2. **Novelty Penalty:** Counts terms in the answer that do NOT appear in the context. Each novel term incurs a 5% penalty (capped at 30%).

3. **Score Calculation:**
   ```
   base_score = coverage_ratio - novelty_penalty
   final_score = clamp(base_score + 0.3, 0.0, 1.0)
   ```

4. **Combined Score:** The LLM's self-reported score and the Critic's heuristic score are averaged with a weighted formula:
   ```
   combined = (llm_score × 0.6) + (critic_score × 0.4)
   ```

5. **Threshold Check:** If `combined_score < 0.6`, the response is flagged as a potential hallucination.

---

### Stage 4: Fallback Regeneration (Groq/Llama-3)

When the Critic Agent rejects a response (faithfulness < 0.6), the system triggers an automatic failover:

1. **Prometheus counter** `verirag_hallucination_rejections_total` is incremented
2. A **stricter prompt** is generated with enhanced constraints:
   - "Previous response failed verification"
   - "Generate a MORE CONSERVATIVE answer"
   - "Only state facts DIRECTLY QUOTED in the context"
3. The strict prompt is sent to **Groq's Llama-3 8B** via OpenAI-compatible API
4. The backup response replaces the original

```python
client = OpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
)
response = client.chat.completions.create(
    model="llama3-8b-8192",
    response_format={"type": "json_object"},
    temperature=0.1
)
```

**Why two models?** Using a different model for regeneration provides architectural redundancy. If Gemini hallucinates on a specific query, Llama-3 with a tighter prompt is less likely to reproduce the same hallucination.

---

### Stage 5: Standardized Response

Every response, regardless of which model generated it, returns a standardized JSON:

```json
{
  "answer": "The factual answer based on documents",
  "faithfulness_score": 0.85,
  "explanation": "Term overlap: 12/15, New terms: 2",
  "source_citation": "Document Title (Page 3)",
  "verification_passed": true,
  "model_used": "gemini",
  "context_chunks_used": 5
}
```

---

## LLM Failover Architecture

The `call_llm_with_fallback()` function implements a two-tier failover:

```
┌──────────────────────┐
│    Incoming Prompt    │
└──────────┬───────────┘
           │
    ┌──────▼──────┐
    │   Gemini    │──── Success ──▶ Return response
    │  (Primary)  │
    └──────┬──────┘
           │ Exception
    ┌──────▼──────┐
    │ Groq/Llama  │──── Success ──▶ Return response + inc(LLM_FALLBACKS)
    │  (Backup)   │
    └──────┬──────┘
           │ Exception
    ┌──────▼──────┐
    │  Error JSON │──── Both failed ──▶ Return error message
    └─────────────┘
```

**Prometheus metrics tracked:**
| Metric | Type | Description |
|--------|------|-------------|
| `verirag_hallucination_rejections_total` | Counter | Responses rejected by Critic Agent |
| `verirag_llm_fallbacks_total` | Counter | Gemini → Groq failovers |
| `verirag_queries_total` | Counter | Total RAG queries processed |
| `verirag_documents_ingested_total` | Counter | Documents successfully vectorized |
| `verirag_faithfulness_score` | Histogram | Distribution of combined faithfulness scores |
| `verirag_active_model` | Gauge | Currently active model (1=Gemini, 2=Groq) |

---

## Document Ingestion Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  Upload  │───▶│ PyPDF    │───▶│ Recursive    │───▶│   Google     │───▶│ pgvector │
│  PDF     │    │ Extract  │    │ Chunker      │    │ Embeddings   │    │ Store    │
│          │    │ Pages    │    │ 1000c/200o   │    │ text-emb-004 │    │          │
└──────────┘    └──────────┘    └──────────────┘    └──────────────┘    └──────────┘
```

1. **Upload:** User uploads PDF via the DocumentViewSet API
2. **Extract:** PyPDF extracts text from all pages
3. **Chunk:** `RecursiveCharacterTextSplitter` splits into 1000-character chunks with 200-character overlap using hierarchical separators (`\n\n`, `\n`, `. `, ` `, `""`)
4. **Embed:** Google's `text-embedding-004` model generates 768-dimensional vectors
5. **Store:** Vectors + metadata stored in PostgreSQL via the pgvector extension

Each chunk carries metadata for multi-tenant isolation:
```python
chunk.metadata = {
    "user_id": str(user.id),
    "document_id": str(doc.id),
    "document_title": doc.title,
    "chunk_index": i
}
```

---

## Async Task Architecture (Celery)

VeriRAG uses Celery with Redis as the message broker for background processing:

| Task | Queue | Schedule | Description |
|------|-------|----------|-------------|
| `ingest_document_task` | `ingestion` | On-demand | Process a single document |
| `process_pending_documents` | `celery` | Every 5 min | Batch process unprocessed docs |
| Celery Beat | — | Continuous | Periodic task scheduler |

Workers listen on multiple queues: `celery`, `ingestion`, `monitoring`, `maintenance`.

---

## Security Architecture

See [SECURITY.md](SECURITY.md) for the complete security model including:
- Azure Key Vault integration for production API key management (with `.env` for local demo)
- JWT authentication via SimpleJWT
- Content Security Policy (CSP) headers
- Multi-tenant data isolation at the vector store level
