# VeriRAG — PhD-Level Evaluation Framework

## 🎯 GOAL
Evaluate if your RAG system actually works for PhD-level research queries.

---

## 📊 PART 1: THE 5 CORE EVALUATION CRITERIA

### ✅ 1. **Context Relevance**
- **Question**: Did the system retrieve the RIGHT documents/chunks?
- **Test**: Query about "RAG" → System should return RAG papers, not random ML stuff
- **Metric**: How many top-5 retrieved chunks are actually relevant?
- **Target**: ≥ 80% of retrieved chunks relevant

### ✅ 2. **Context Sufficiency**
- **Question**: Is the retrieved data ENOUGH to answer?
- **Test**: Query asking for "methodology" → need methods section, not just abstract
- **Metric**: Does retrieved content have enough detail to answer fully?
- **Target**: Answer can be fully answered from retrieved context alone

### ✅ 3. **Answer Correctness**
- **Question**: Is the answer factually correct?
- **Test**: Manual verification against source papers
- **Metric**: Fact-checking score
- **Target**: 95%+ factual accuracy

### ✅ 4. **Groundedness (MOST IMPORTANT)**
- **Question**: Is answer based on evidence? Can you trace it?
- **Test**: Every claim in answer must cite a source
- **Metric**: % of claims with citations
- **Target**: 100% of claims cited

### ✅ 5. **Hallucination Rate**
- **Question**: Did it invent anything unsupported by sources?
- **Test**: Cross-reference claims with source documents
- **Metric**: % of hallucinated statements
- **Target**: 0% hallucinations

---

## 🧪 PART 2: TEST QUERIES (DESIGNED FOR YOUR SYSTEM)

### Basic Tests (Should always pass)
```
1. Query: "What is RAG?"
   Expected: Definition, key components, why it matters
   Retrieval: RAG papers (arxiv 2304.*, OpenAI blog)
   Grounding: Citations to original papers
   Verdict: PASS if cites source papers

2. Query: "How does RAG reduce hallucination?"
   Expected: Mechanism explanation, evidence
   Retrieval: Papers on hallucination + RAG
   Grounding: Method section citations
   Verdict: PASS if explains with evidence

3. Query: "What is a vector database?"
   Expected: Purpose, use case, examples
   Retrieval: pgvector docs, vector DB papers
   Grounding: Specific implementations cited
   Verdict: PASS if accurate technical explanation
```

### Advanced Tests (Research-level)
```
4. Query: "Compare RAG vs fine-tuning for knowledge grounding"
   Expected: Pros/cons, when to use each
   Retrieval: Multiple papers, comparison studies
   Grounding: Citations to each method's trade-offs
   Verdict: PASS if nuanced, evidence-based

5. Query: "What method did [specific paper] use for chunking?"
   Expected: Exact extraction from paper
   Retrieval: Target paper + context
   Grounding: Direct quote or close paraphrase
   Verdict: PASS if accurate extraction

6. Query: "How does pgvector indexing work?"
   Expected: Technical implementation details
   Retrieval: pgvector docs, proximity search
   Grounding: Architecture citations
   Verdict: PASS if technically correct
```

### Rejection Tests (Should NOT hallucinate)
```
7. Query: "Explain turboquant"
   Expected: Either found with grounding OR "No evidence found"
   ❌ FAIL: System guesses/hallucinates explanation
   ✅ PASS: System says "No sufficient evidence" if not in docs

8. Query: "What is GraphRAG?"
   Expected: Found → answer. Not found → reject
   Grounding: If found, must cite source
   Verdict: PASS if honest about knowledge limits

9. Query: "Compare VeriRAG vs [unknown system]"
   Expected: Reject or find via web search
   Verdict: PASS if doesn't hallucinate comparison
```

---

## 📋 PART 3: MANUAL EVALUATION TEMPLATE

Use this for each query:

```
Query: [Your question]
────────────────────────────────────────

RETRIEVAL PHASE:
Top-5 Retrieved Chunks:
  1. [Chunk text] — Source: [paper/doc]
  2. ...
  
Relevance Score: [ ] /10
  (Are chunks actually relevant?)

Sufficiency Score: [ ] /10
  (Is info enough to answer?)

────────────────────────────────────────

GENERATION PHASE:
Generated Answer:
  [Full answer text]

Correctness Score: [ ] /10
  (Is it factually accurate?)

Grounding Analysis:
  ✅ Claim 1: [Cited? YES/NO] → Source: [...]
  ✅ Claim 2: [Cited? YES/NO] → Source: [...]
  ❌ Claim 3: [Unsupported?]

Grounding Score: [ ] /10
  (% of claims with citations)

Hallucination Score: [ ] /10
  (0 = no hallucination, 10 = severe)

────────────────────────────────────────

FINAL VERDICT:
- Relevance: [ ] /10
- Sufficiency: [ ] /10
- Correctness: [ ] /10
- Grounding: [ ] /10
- No Hallucination: [ ] /10

OVERALL: PASS / NEEDS IMPROVEMENT / FAIL

Comments:
  - What worked?
  - What broke?
  - What to improve?
```

---

## 🔧 PART 4: EVALUATION SCRIPT (Python)

Save as `tests/evaluate_rag.py`:

```python
"""
Automated RAG Evaluation Script
"""
import json
import time
from typing import Dict, List

# TEST QUERIES
TEST_QUERIES = [
    {
        "id": "basic_1",
        "query": "What is RAG?",
        "category": "basic",
        "expect_retrieval": True,
        "min_confidence": 0.7,
    },
    {
        "id": "basic_2",
        "query": "How does RAG reduce hallucination?",
        "category": "basic",
        "expect_retrieval": True,
        "min_confidence": 0.7,
    },
    {
        "id": "advanced_1",
        "query": "Compare RAG vs fine-tuning",
        "category": "advanced",
        "expect_retrieval": True,
        "min_confidence": 0.75,
    },
    {
        "id": "rejection_1",
        "query": "Explain turboquant",
        "category": "rejection",
        "expect_retrieval": False,  # Should gracefully fail or search web
        "min_confidence": 0.0,
    },
]

def evaluate_single_query(query: str, system_response: Dict) -> Dict:
    """
    Evaluate a single RAG response
    """
    return {
        "query": query,
        "confidence": system_response.get("confidence", 0),
        "method": system_response.get("method"),  # direct/synthesis/rejected
        "has_answer": system_response.get("answer") is not None,
        "citations": len(system_response.get("citations", [])),
        "latency_ms": system_response.get("latency_ms"),
        "cost_usd": system_response.get("cost_usd"),
    }

def run_evaluation():
    """
    Run full evaluation suite
    """
    results = []
    
    # Import backend
    import os
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_backend.settings")
    django.setup()
    
    from ai_engine.core_rag import answer_academic_question
    
    # Test with user_id = 1 (or create test user)
    user_id = 1
    
    print("🧪 Running RAG Evaluation Suite...")
    print("=" * 60)
    
    for test in TEST_QUERIES:
        query = test["query"]
        print(f"\n📝 Query: {query}")
        print(f"   Category: {test['category']}")
        
        start = time.time()
        response = answer_academic_question(query, user_id)
        latency = time.time() - start
        
        result = evaluate_single_query(query, response)
        result["test_id"] = test["id"]
        result["category"] = test["category"]
        result["expected_retrieval"] = test["expect_retrieval"]
        result["latency"] = latency
        
        results.append(result)
        
        # Print summary
        print(f"   ✓ Confidence: {response.get('confidence', 0):.2f}")
        print(f"   ✓ Method: {response.get('method')}")
        print(f"   ✓ Citations: {len(response.get('citations', []))}")
        print(f"   ✓ Latency: {latency*1000:.0f}ms")
        
        if response.get("answer"):
            preview = response["answer"][:100] + "..."
            print(f"   ✓ Answer: {preview}")
        else:
            print(f"   ✓ Answer: [REJECTED/NO ANSWER]")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r["has_answer"])
    rejected = total - passed
    avg_confidence = sum(r["confidence"] for r in results) / total
    avg_latency = sum(r["latency"] for r in results) / total
    
    print(f"Total Tests: {total}")
    print(f"Answered: {passed} ({passed/total*100:.0f}%)")
    print(f"Rejected: {rejected} ({rejected/total*100:.0f}%)")
    print(f"Avg Confidence: {avg_confidence:.2f}")
    print(f"Avg Latency: {avg_latency*1000:.0f}ms")
    
    # Save results
    with open("tests/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Results saved to tests/evaluation_results.json")

if __name__ == "__main__":
    run_evaluation()
```

---

## 🚀 PART 5: HOW TO USE THIS WITH CLAUDE

### Step 1: Run evaluation
```bash
cd apps/backend
python ../../tests/evaluate_rag.py
```

### Step 2: Copy results into Claude prompt:
```
You are a research evaluator for a RAG system.

EVALUATION CRITERIA:
1. Context relevance (are correct docs retrieved?)
2. Context sufficiency (is data enough?)
3. Answer correctness (is it accurate?)
4. Groundedness (are claims cited?)
5. Hallucination (any unsupported claims?)

Now evaluate this response:

Query: "What is RAG?"

System Output:
[Paste answer here]

Retrieved Chunks:
[Paste chunks here]

Citations:
[Paste citations here]

Evaluate using this structure:
- Relevance: [score] /10 [reason]
- Sufficiency: [score] /10 [reason]
- Correctness: [score] /10 [reason]
- Grounding: [score] /10 [reason]
- Hallucination: [score] /10 [reason]

Final Verdict: PASS / NEEDS IMPROVEMENT / FAIL
```

---

## 🎯 PART 6: SUCCESS CRITERIA FOR PhD-LEVEL RAG

Your system is **WORKING** when:

| Metric | Target | Current |
|--------|--------|---------|
| Context Relevance | ≥ 80% | ? |
| Answer Correctness | ≥ 95% | ? |
| Groundedness | 100% cited | ? |
| Hallucination Rate | 0% | ? |
| Confidence Calibration | Match actual accuracy | ? |
| Latency | < 1s | ? |
| Cost per query | < $0.01 | ? |

---

## 📝 NEXT STEPS

1. **Run the evaluation script** above
2. **Test with the 9 queries** from Part 2
3. **Capture results** in the manual template
4. **Ask Claude** to evaluate using the structured prompt
5. **Identify failure modes**:
   - Bad retrieval? → Improve embeddings
   - Bad generation? → Better LLM or prompt
   - Hallucination? → Stricter grounding rules
6. **Iterate** and re-evaluate

---

## 🧠 KEY INSIGHT

Most RAG systems fail at **grounding**, not retrieval.

They can find papers, but they:
- ❌ Don't cite correctly
- ❌ Invent details not in sources
- ❌ Synthesize incorrectly

Your system passes when every claim is traceable to a source document.

