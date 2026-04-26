# 🚀 VeriRAG with arXiv & Patent Search Integration

## Overview

Your RAG system now includes **live integration with**:
- ✅ **arXiv** (650k+ research papers)
- ✅ **Semantic Scholar** (190M+ papers with citation data)
- ✅ **USPTO Patents** (10M+ patents)
- ✅ **Google Patents** (Easier than USPTO)

When local documents don't provide sufficient context, the system automatically searches these sources.

---

## 🎯 How It Works

### Traditional RAG Flow (Local Only)
```
User Query → Search Local Documents → Generate Answer
```

### Hybrid RAG Flow (Local + Web)
```
User Query
    ↓
Search Local Documents
    ↓
Low Confidence? (< 0.7)
    ├─ YES → Search arXiv + Semantic Scholar + Patents
    │         Blend with local results
    │         Generate grounded answer
    ├─ NO  → Generate from local docs only
    ↓
Answer with Citations
```

---

## 🌐 Quick Start

### 1. Launch the System

```powershell
# Option A: Automated launch
powershell -ExecutionPolicy Bypass -File docker-launch.ps1

# Option B: Manual launch
docker-compose up -d
```

### 2. Test the APIs

```powershell
# Search arXiv
curl -X POST http://localhost:8000/api/search/arxiv/ `
  -H "Content-Type: application/json" `
  -d '{"query":"RAG retrieval augmented generation", "max_results":5}'

# Search papers (arXiv + Semantic Scholar)
curl -X POST http://localhost:8000/api/search/papers/ `
  -H "Content-Type: application/json" `
  -d '{"query":"machine learning", "max_results":10}'

# Search patents
curl -X POST http://localhost:8000/api/search/patents/ `
  -H "Content-Type: application/json" `
  -d '{"query":"neural networks", "max_results":10}'

# Augment RAG with web search
curl -X POST http://localhost:8000/api/search/augment-rag/ `
  -H "Content-Type: application/json" `
  -d '{"query":"what is turboquant?", "local_confidence":0.3}'
```

---

## 📚 API Reference

### POST `/api/search/arxiv/`
Search arXiv for research papers

**Request:**
```json
{
  "query": "RAG retrieval augmented generation",
  "max_results": 10,
  "sort_by": "relevance"  // or "submittedDate"
}
```

**Response:**
```json
{
  "source": "arXiv",
  "query": "RAG retrieval augmented generation",
  "count": 10,
  "results": [
    {
      "source": "arXiv",
      "arxiv_id": "2304.06098",
      "title": "Retrieval-Augmented Generation for Large Language Models: A Survey",
      "authors": ["Wenhao Yu", "Zhihan Zhang", ...],
      "summary": "...",
      "published": "2023-04-12T17:59:58Z",
      "pdf_url": "http://arxiv.org/pdf/2304.06098v1",
      "categories": "cs.CL",
      "relevance_score": 0.95
    }
  ]
}
```

### GET `/api/search/arxiv-latest/?category=cs.AI&days=7`
Get latest papers by category

**Parameters:**
- `category`: cs.AI, cs.LG, cs.CL, cs.CV, cs.CR, etc.
- `days`: Number of days to look back (default: 7)
- `max_results`: Max results (default: 20)

### POST `/api/search/papers/`
Search academic papers (arXiv + Semantic Scholar combined)

**Request:**
```json
{
  "query": "vector databases",
  "max_results": 20
}
```

**Response includes:**
- arXiv papers with PDFs
- Semantic Scholar papers with citation counts
- Combined ranking by relevance

### POST `/api/search/patents/`
Search patents (USPTO + Google Patents)

**Request:**
```json
{
  "query": "machine learning classification",
  "max_results": 15
}
```

**Response includes:**
- USPTO patents
- Google Patents
- Filing dates, assignees, inventors

### POST `/api/search/all/`
Search all sources at once

**Request:**
```json
{
  "query": "quantum computing",
  "sources": ["arxiv", "semantic_scholar", "patents"],
  "max_per_source": 10
}
```

### POST `/api/search/augment-rag/`
Automatically search web when local confidence is low

**Request:**
```json
{
  "query": "what is turboquant?",
  "local_confidence": 0.5,
  "search_papers": true,
  "search_patents": false
}
```

**Response:**
```json
{
  "query": "what is turboquant?",
  "local_confidence": 0.5,
  "augmented": true,
  "count": 12,
  "results": [...]
}
```

---

## 🧪 Test Queries (Designed for Web Search)

These queries test the web search fallback:

```
1. "Explain turboquant"
   → Expected: Searches arXiv/web for turboquant papers

2. "What is GraphRAG?"
   → Expected: Finds GraphRAG paper, grounded answer

3. "Compare RAG vs fine-tuning for knowledge"
   → Expected: Multiple papers, synthesis

4. "Recent advances in vector databases (2024)"
   → Expected: Latest papers on arXiv

5. "Patent for neural network compression"
   → Expected: USPTO/Google Patents results

6. "How does retrieval-augmented generation work?"
   → Expected: arXiv papers + Semantic Scholar

7. "What is the LLMCat database?"
   → Expected: Either finds paper or gracefully rejects

8. "Hybrid search algorithms"
   → Expected: Academic papers on hybrid search

9. "Patents on prompt engineering"
   → Expected: Patent results from USPTO
```

---

## 🔧 Configuration

### In `.env`:
```env
# No additional config needed! 
# All APIs are free and don't require keys

# Optional: Rate limiting
ARXIV_RATE_LIMIT=3/second  # Max requests per second
SEMANTIC_SCHOLAR_TIMEOUT=10  # Seconds
USPTO_TIMEOUT=15
```

### In `apps/backend/ai_engine/external_search.py`:
Adjust thresholds:
```python
# Low relevance threshold = more web searches
CONFIDENCE_MID = 0.70  # Search web if confidence < 0.70

# Increase max results per source
max_per_source = 20  # Default: 10
```

---

## 📊 Integration in RAG Pipeline

The web search is **automatically triggered** when:

1. **No local documents match** (empty result set)
2. **Confidence is low** (< 0.70)
3. **Query is about recent work** (papers published < 6 months ago)
4. **User requests specific papers** ("What did paper X say about...")

### Code Integration

In `apps/backend/ai_engine/core_rag.py`:

```python
from ai_engine.external_search import augment_rag_with_web_search

# After retrieving local chunks:
if confidence < CONFIDENCE_MID:
    # Augment with web search
    augmented = augment_rag_with_web_search(
        query=query,
        local_chunks=chunks,
        search_web=True,
        search_patents=True,
    )
    
    # Blend results
    all_chunks = chunks + augmented["web_papers"]
    answer = generate_answer_from_mixed_sources(all_chunks)
```

---

## 📈 Expected Behavior

### Scenario 1: "What is RAG?"
```
Local search → Finds 5 papers on RAG
Confidence: 0.88 (HIGH)
Action: Answer from local docs only
Result: "RAG is Retrieval-Augmented Generation..."
```

### Scenario 2: "What is turboquant?"
```
Local search → 0 papers found
Confidence: 0.0 (NO DATA)
Action: Search arXiv + Semantic Scholar
Result: (If found) "TurboQuant is a method for..."
        (If not found) "No sufficient evidence about turboquant"
```

### Scenario 3: "Recent advances in RAG (2024)"
```
Local search → 2 papers (from 2023)
Confidence: 0.45 (LOW - outdated)
Action: Search arXiv for latest papers
Result: Blended answer with 2023 + 2024 papers
```

---

## 🎯 Evaluation Framework Update

The evaluation now tests **web search grounding**:

```python
# From RAG_EVALUATION_FRAMEWORK.md

Test 7: "Explain turboquant"
- If in local docs → cite source
- If found on arXiv → cite arXiv ID
- If not found → "No reliable evidence"
- ❌ FAIL: System hallucinates explanation

Test 9: "Compare VeriRAG vs unknown-system"
- If unknown-system not in any source → REJECT
- ✅ PASS: Honest about knowledge limits
```

---

## 🔍 Troubleshooting

### "arXiv search returns 0 results"
```
Possible causes:
1. Query too specific (use broader terms)
2. Network timeout (check internet connection)
3. arXiv API rate limited (wait a minute)

Solution:
- Try simpler query: "machine learning" vs "federated learning with differential privacy"
- Check arXiv status: https://arxiv.org/
```

### "Patent search is slow"
```
Possible causes:
1. USPTO API is slow (takes 10-15 seconds)
2. Network latency
3. Large result set being processed

Solution:
- Reduce max_results: max_results=5
- Use Google Patents only: sources=["google_patents"]
```

### "Semantic Scholar returns no results"
```
The API has stricter rate limiting (1 request per second)

Solution:
- Add delay between requests
- Reduce concurrent searches
```

---

## 📚 Data Source Details

### arXiv
- **Coverage**: Computer Science, Physics, Math, Stats
- **Rate Limit**: 3 requests/second
- **API**: Free, no key required
- **Data**: 2.3M papers, daily updates
- **URL**: https://arxiv.org/help/api/

### Semantic Scholar
- **Coverage**: 190M papers, all fields
- **Rate Limit**: 100 requests/minute (free)
- **API**: Free, no key required
- **Data**: Citation counts, influential citations
- **URL**: https://www.semanticscholar.org/product/api

### USPTO Patents
- **Coverage**: 10M+ US patents
- **Rate Limit**: None specified
- **API**: Free public API
- **Data**: Patent number, inventor, assignee, dates
- **URL**: https://www.uspto.gov/

### Google Patents
- **Coverage**: All patents (US, EU, WIPO, etc.)
- **Rate Limit**: Strict (1-2 requests/second)
- **API**: Free via public search
- **Data**: Clear interface, citations to other patents
- **URL**: https://patents.google.com/

---

## 🚀 Advanced: Custom Search Sources

To add your own data source:

```python
# In apps/backend/ai_engine/external_search.py

class CustomSearcher:
    """Search your custom data source"""
    
    @staticmethod
    def search(query: str, max_results: int = 10):
        # Implementation
        results = [
            {
                "source": "CustomSource",
                "title": "...",
                "url": "...",
                "relevance_score": 0.8,
            }
        ]
        return results

# Register in UnifiedResearchSearcher:
def search_all(query, sources=None):
    results = {}
    if "custom" in sources:
        results["custom"] = CustomSearcher.search(query)
    return results
```

---

## 📊 Next Steps

1. **Test the APIs** above
2. **Run evaluation framework** with web search enabled
3. **Deploy to Azure** with API calls to external sources
4. **Monitor API usage** (all are free but have rate limits)
5. **Add custom sources** as needed

---

## 🔗 Useful Links

- arXiv API: https://arxiv.org/help/api/user-manual
- Semantic Scholar: https://www.semanticscholar.org/product/api
- USPTO: https://developer.uspto.gov/
- Google Patents: https://patents.google.com/
- Patent search docs: https://patents.google.com/about/search

