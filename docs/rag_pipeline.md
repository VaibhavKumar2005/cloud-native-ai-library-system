# RAG Pipeline – Technical Details

This document describes the Retrieval-Augmented Generation (RAG) pipeline used by VeriRAG, with emphasis on verification and grounding.

---

## Pipeline Overview

```
Query Input
    ↓
[1] Query Embedding      → Google text-embedding-004
    ↓
[2] Vector Retrieval     → pgvector similarity search
    ↓
[3] Ranking              → Order by relevance scores
    ↓
[4] Confidence Decision  → Direct/Synthesis/Reject
    ↓
[5] Generation (if needed) → LLM synthesis
    ↓
[6] Verification        → Faithfulness scoring
    ↓
[7] Citation Extraction  → Trace to source chunks
    ↓
Response with Confidence Score
```

---

## Stage 1: Query Embedding

**Input**: Natural language question  
**Output**: 512-dimensional vector

```python
from langchain.embeddings import GooglePalmEmbeddings

embedding_model = GooglePalmEmbeddings(
    model_name="models/text-embedding-004",
    google_api_key=GOOGLE_API_KEY
)

query_vector = embedding_model.embed_query(user_question)
# Shape: (512,)
```

**Cost**: $0.00006 per query (100% of queries)  
**Latency**: 200-500ms (mostly network roundtrip)  
**Caching**: Previous queries cached in Redis

---

## Stage 2: Vector Retrieval

**Input**: Query vector  
**Output**: Top-K relevant document chunks

### Similarity Search

```sql
SELECT 
  chunk_id,
  document_id,
  content,
  1 - (embedding <=> query_embedding) AS similarity_score
FROM document_chunks
WHERE document_id = user_document_id
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

**Distance Metric**: L2 (Euclidean) via pgvector's `<=>` operator  
**Index Type**: HNSW (Hierarchical Navigable Small Worlds)  
**Typical Latency**: 50-100ms for 1M vectors  

**Performance Notes**:
- Embedding dimension: 512 (smaller = faster, but less expressive)
- Index size: ~512 bytes/vector + HNSW overhead
- Search complexity: O(log n) average case

---

## Stage 3: Ranking & Filtering

### Confidence Calculation

```python
def calculate_confidence(top_chunks):
    """
    Confidence = combination of:
    1. Top chunk similarity (most important)
    2. Consistency across top-5 results
    3. Density of relevant results
    """
    if not top_chunks:
        return 0.0
    
    top_similarity = top_chunks[0].similarity
    
    # How many chunks are above relevance threshold?
    relevant_count = sum(1 for c in top_chunks if c.similarity >= 0.70)
    consistency = relevant_count / len(top_chunks)
    
    # Weighted combination
    confidence = (top_similarity * 0.6) + (consistency * 0.4)
    
    return min(1.0, confidence)
```

### Tier Decision Tree

```
confidence >= 0.88?
  ├─ YES + is_qa_chunk → TIER 1: Direct Retrieval
  ├─ NO (0.70-0.88) → TIER 2: LLM Synthesis
  └─ NO (< 0.70) → TIER 3: Graceful Rejection
```

| Tier | Confidence | Cost | Latency | Action |
|------|-----------|------|---------|--------|
| 1 | ≥0.88 | $0.00006 | <50ms | Return chunk directly |
| 2 | 0.70-0.88 | $0.0005 | 1-3s | Call LLM |
| 3 | <0.70 | $0 | <100ms | Reject |

---

## Stage 4A: Direct Retrieval (Tier 1)

**When**: High confidence + Q&A formatted chunk

**Process**:
1. Take top chunk
2. Format with metadata (source, page, authors)
3. Generate BibTeX citation
4. Return to user

**No LLM involved** – purely retrieval-based.

**Example**:
```
Q: "What is RAG?"
→ Vector search finds chunk (similarity: 0.94)
→ Chunk: "RAG (Retrieval-Augmented Generation) combines document retrieval..."
→ Return directly with citation
```

---

## Stage 4B: LLM Synthesis (Tier 2)

**When**: Medium confidence (0.70-0.88)

**Prompt Design**:
```python
SYNTHESIS_PROMPT = """
You are a citation-grounded research assistant.

CONTEXT (from retrieved documents):
{retrieved_chunks}

USER QUESTION:
{question}

INSTRUCTIONS:
1. Answer ONLY using the context above
2. If context is insufficient, say "Insufficient evidence"
3. Every claim must be traceable to the context
4. Keep answer concise (2-3 sentences)

ANSWER:
"""
```

**Key Features**:
- Forces grounding in retrieved context
- Explicit instruction against hallucination
- Token limit (200 max) prevents verbose responses

**Model Parameters**:
```
temperature = 0.7        # Some creativity, but grounded
max_tokens = 200        # Force conciseness
top_p = 0.9            # Diverse but focused sampling
```

**Cost**: ~$0.0005 per call (input + output tokens)  
**Latency**: 1-3 seconds (mostly waiting for LLM)

---

## Stage 4C: Graceful Rejection (Tier 3)

**When**: Low confidence (<0.70)

**Response**:
```json
{
  "answer": null,
  "rejection_reason": "Insufficient evidence in your papers",
  "confidence": 0.35,
  "suggestion": "Try uploading more relevant papers or refining your question",
  "similar_topics": ["topic1", "topic2"]
}
```

**Why Rejection Matters**:
- Prevents hallucinated answers
- Honest about system limitations
- Better than guessing for research

---

## Stage 5: Verification

### Semantic Faithfulness Check

**Method**: Embedding cosine similarity

```python
def verify_faithfulness(answer: str, context: str) -> float:
    """
    Verify answer is grounded in context using embeddings.
    
    If embedding(answer) ≈ embedding(context), then answer likely grounded.
    """
    answer_emb = embedding_model.embed_query(answer)
    context_emb = embedding_model.embed_query(" ".join(context))
    
    from sklearn.metrics.pairwise import cosine_similarity
    similarity = cosine_similarity([answer_emb], [context_emb])[0][0]
    
    # Normalize to 0-1 range
    score = max(0.0, min(1.0, similarity))
    
    return score
```

**Interpretation**:
- **0.0-0.3**: High hallucination risk
- **0.3-0.6**: Moderate risk
- **0.6-0.8**: Good grounding
- **0.8-1.0**: Excellent grounding

**Threshold**: 0.6 (must reach this to return answer)

**Cost**: Reuses cached embeddings (no additional API call)  
**Latency**: <50ms

### Optional: RAGAS Evaluation

For higher confidence, optional RAGAS framework provides:

```python
ragas_scores = {
    "faithfulness": 0.92,         # Grounded in context?
    "answer_relevancy": 0.90,     # Addresses question?
    "context_precision": 0.88,    # Relevant chunks?
    "context_recall": 0.0,        # Comprehensive retrieval? (requires ground truth)
}

# Weighted combination (faithfulness most critical)
combined = (
    0.92 * 0.5 +    # faithfulness: 50%
    0.90 * 0.3 +    # answer_relevancy: 30%
    0.88 * 0.2      # context_precision: 20%
)
# = 0.906
```

**Cost**: Additional LLM call (~$0.0001)  
**Latency**: +1-2 seconds

---

## Stage 6: Citation Extraction

### Automatic Citation Linking

```python
def extract_citations(answer: str, source_chunks: list) -> list:
    """
    Link each sentence in answer to source chunks.
    """
    citations = []
    
    for sentence in answer.split(". "):
        best_match = find_most_similar_chunk(sentence, source_chunks)
        
        if best_match.similarity > 0.5:  # Confidence threshold
            citations.append({
                "sentence": sentence,
                "source": best_match.document_title,
                "page": best_match.page_number,
                "authors": best_match.authors,
                "similarity": best_match.similarity
            })
    
    return citations
```

### Citation Validation

```python
def validate_citation(claim: str, cited_chunk: str) -> bool:
    """
    Verify that cited chunk actually supports the claim.
    """
    claim_emb = embedding_model.embed_query(claim)
    chunk_emb = embedding_model.embed_query(cited_chunk)
    
    similarity = cosine_similarity([claim_emb], [chunk_emb])[0][0]
    
    return similarity >= 0.6  # Must be similar enough
```

---

## Configuration Parameters

### Retrieval
```
TOP_K_CHUNKS = 10              # Number of chunks to retrieve
CHUNK_SIZE = 512               # Tokens per chunk
CHUNK_OVERLAP = 0.5            # 50% overlap for continuity
SIMILARITY_THRESHOLD = 0.3     # Min similarity to consider
```

### Confidence & Routing
```
TIER1_THRESHOLD = 0.88         # Direct retrieval minimum
TIER2_THRESHOLD = 0.70         # Synthesis minimum
FAITHFULNESS_THRESHOLD = 0.60  # Overall acceptance minimum
```

### Caching
```
CACHE_TTL_SECONDS = 86400      # 24 hour cache
CACHE_HIT_RATE_TARGET = 0.5    # Expected hit rate
```

### LLM
```
TEMPERATURE = 0.7              # Creativity level
MAX_TOKENS = 200               # Max response length
LLM_TIMEOUT = 30               # Seconds before fallback
```

---

## Error Handling & Fallbacks

### LLM Unavailable
```
If Gemini fails:
  → Retry with Groq/Llama-3
  
If both fail:
  → Return Tier 1 answer (direct retrieval, no synthesis)
  → Or reject if no good Tier 1 match
```

### Verification Fails
```
If verification score < 0.6:
  → Trigger fallback LLM (different model)
  → Re-verify synthesis answer
  → If still fails, reject
```

### Database Unavailable
```
Cache hits served from Redis (no DB needed)
Cache misses: Query cannot proceed (graceful error)
```

---

## Metrics & Monitoring

### Prometheus Metrics

```
verirag_queries_total              # Total queries processed
verirag_queries_by_tier            # Breakdown by tier (1/2/3)
verirag_verification_rejections    # Failed verifications
verirag_faithfulness_score         # Distribution of scores
verirag_llm_calls_total            # LLM API calls
verirag_cache_hits_total           # Cache hits
```

### Example Query Trace

```
[14:32:01.234] Query: "What is RAG?" (user_id=123)
├─ [14:32:01.241] Cache check: MISS
├─ [14:32:01.245] Embed query: 6ms, $0.00006
├─ [14:32:01.297] Vector search: 52ms, 10 chunks found
│  └─ Top similarity: 0.94 (chunk_id=567)
├─ [14:32:01.298] Tier decision: DIRECT (confidence 0.88)
├─ [14:32:01.320] Semantic verification: 0.92 ✅ PASS
├─ [14:32:01.325] Citation extraction: 3 citations found
├─ [14:32:01.330] Format response
├─ [14:32:01.335] Cache store: 24h TTL
└─ [14:32:01.336] Return (95ms total, $0.00006 cost)
```

---

## Research Implications

### Reproducibility
- All queries logged to `RAG_EVAL_LOG/`
- Includes: query, retrieved chunks, scores, citations
- Allows auditing and replication

### Verification Limitations
- Embedding-based verification may miss subtle factual errors
- Citation extraction is heuristic (some citations may be missed)
- No ground truth to validate if papers themselves contain errors

### Cost-Quality Trade-off
- Tier 1 (direct): Cheapest, fastest, high precision
- Tier 2 (synthesis): More flexible, handles complex queries
- Tier 3 (rejection): Zero cost, prevents misinformation

---

See also: [Evaluation Framework](evaluation.md), [Deployment](deployment.md)
