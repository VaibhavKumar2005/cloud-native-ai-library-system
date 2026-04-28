# VeriRAG – Verified Research Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Research Grade](https://img.shields.io/badge/status-research%20grade-blue)]()
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)

---

## 🎓 What This Project Does

VeriRAG is an **evidence-based question-answering system for academic research**. Given a collection of research papers (PDFs), it answers questions with citations to source material and automatically rejects queries when evidence is insufficient.

Unlike general-purpose LLMs, VeriRAG operates under one core constraint: **it cannot and will not invent information**. Every claim in an answer must be traceable to a retrieved document.

**Key distinction**: This is not a RAG chatbot for customer service. This is a research verification system designed for PhD-level work where citation accuracy is non-negotiable.

---

## 🧠 The Research Problem

### Why This Matters

Large language models **hallucinate**. They generate plausible-sounding text that is completely false. When a researcher asks "What does [Paper X] say about chunking?", a standard LLM might:
- Invent authors who don't exist
- Cite methods from other papers
- Create results that were never reported

For academic research, these errors are catastrophic. A paper built on hallucinated evidence becomes retractable.

### The Solution: Grounded Answer Generation

VeriRAG addresses this through:

1. **Retrieval-Augmented Generation (RAG)**: Answer only from papers you've uploaded
2. **Verification**: Score each answer for faithfulness to source material
3. **Rejection**: Refuse to answer if confidence is insufficient
4. **Citation Grounding**: Every claim includes source references

**Result**: When VeriRAG says something, you can verify it against your papers.

---

## 📚 How It Works (Research Workflow)

```
Researcher uploads PDF papers
           ↓
Question: "How does RAG reduce hallucination?"
           ↓
[1] RETRIEVE → Vector search finds relevant paper sections
           ↓
[2] RANK → Order by relevance (semantic similarity)
           ↓
[3] SYNTHESIZE → Generate coherent answer from top sections
           ↓
[4] VERIFY → Check if answer is grounded in retrieved text
           ↓
[5] RETURN/REJECT → 
    If confidence ≥ 0.6: Return with citations
    If confidence < 0.6: "Insufficient evidence in your papers"
```

**Core principle**: Every response is either grounded (return with citations) or rejected. There is no "guess" option.

---

## 🔬 Academic Paper Integration

### Supported Input Formats
- **PDF research papers** (uploaded via UI)
- **arXiv papers** (via API integration, if enabled)
- **Semantic Scholar** (paper metadata and abstracts, if enabled)
- **Plain text documents** (technical reports, theses, etc.)

### Processing Pipeline

1. **Ingestion**: Extract text from PDFs using OCR-aware extraction
2. **Chunking**: Divide papers into semantic units (~512 tokens)
3. **Embedding**: Convert chunks to vector representations (512-dim)
4. **Indexing**: Store in pgvector for similarity search
5. **Metadata**: Preserve source (title, authors, publication date, page number)

### Citation Extraction & Verification

When an answer is generated, VeriRAG traces it back to source:
```
Answer: "Semantic chunking divides documents by meaning, not fixed length."

Citation: 
- Source: "Langchain Documentation"
- Location: "Section 3.2, Page 8"
```

VeriRAG validates that citations actually support the claim by checking semantic overlap between the answer and the retrieved text.

**Assumption**: Citation validation uses embedding similarity. Perfect accuracy requires manual verification for publication-grade work.

---

## 📖 Example Research Sessions

### Session 1: Valid Question (Should Answer)

```
Q: "What is semantic chunking according to the papers?"

System retrieval:
→ Found 3 relevant sections (similarity: 0.88, 0.79, 0.75)
→ Top result: "Semantic chunking divides text by meaning..."
→ Confidence: HIGH (0.88 ≥ 0.6 threshold)

Answer:
"Semantic chunking divides documents into logical units based on meaning 
rather than fixed token counts. This approach preserves contextual 
relationships and improves retrieval quality in RAG systems.

Sources:
[1] Langchain - Semantic Chunking Guide, Section 3.2
[2] Research Paper X - Methods, Page 12"

Status: ✅ GROUNDED (verified against source material)
```

### Session 2: Insufficient Evidence (Should Reject)

```
Q: "How does the system handle quantum-resistant cryptography?"

System retrieval:
→ Found 1 loosely related section (similarity: 0.35)
→ Confidence: LOW (0.35 < 0.6 threshold)

Answer:
"I cannot answer this question reliably. Your uploaded papers do not 
contain sufficient information about quantum-resistant cryptography. 
Please upload papers specifically addressing this topic."

Status: ❌ REJECTED (honest about knowledge limits)
```

---

## 🧪 Evaluation & Grounding

### What Gets Tracked

For every query, VeriRAG logs:

```json
{
  "query": "What is RAG?",
  "timestamp": "2024-01-15T10:32:01Z",
  "retrieval": {
    "papers_searched": 42,
    "chunks_returned": 10,
    "top_similarity": 0.94,
    "relevance_distribution": [0.94, 0.87, 0.81, ...]
  },
  "verification": {
    "faithfulness_score": 0.92,
    "all_claims_cited": true,
    "verification_passed": true
  },
  "response": {
    "answer": "RAG is Retrieval-Augmented Generation...",
    "citations": ["Source A", "Source B"],
    "confidence": 0.92,
    "method": "DIRECT_RETRIEVAL"
  }
}
```

### Evaluation Metrics (RAG-Specific)

**Context Relevance**: Are retrieved chunks actually relevant to the query?
- Measured: Semantic similarity of top-k chunks
- Target: ≥ 0.70 average similarity

**Faithfulness**: Is the answer grounded in retrieved content?
- Measured: Embedding cosine similarity (answer vs. context)
- Target: ≥ 0.60 (prevents hallucinations)

**Citation Correctness**: Do citations actually support claims?
- Measured: Manual validation
- Target: 100% of claims traceable to source

**Rejection Accuracy**: When system rejects, is it justified?
- Measured: Manual review of rejected queries
- Target: <5% false rejections

Every 100 queries, VeriRAG generates a report (`RAG_EVAL_LOG/`) with these metrics.

---

## 🏗 Architecture (Research-Oriented)

### Core Components

```
Research Interface (React)
        ↓
  REST API (Django)
        ↓
RAG Pipeline Engine
├─ [Retrieve] pgvector search
├─ [Rank] Similarity scoring
├─ [Synthesize] LLM generation
├─ [Verify] Faithfulness check
└─ [Format] Citation extraction
        ↓
Embedding Model (Google)
Vector Store (PostgreSQL+pgvector)
LLM APIs (Gemini, Groq)
Redis Cache
```

### Technology Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| **Embeddings** | Google text-embedding-004 | Proven on academic texts |
| **Vector Store** | PostgreSQL + pgvector | Self-hosted, reproducible |
| **LLM** | Google Gemini 1.5 Flash | Fast, cost-effective |
| **Fallback** | Groq Llama-3 8B | Open source, transparent |
| **Caching** | Redis | Reduces API costs |

---

## ⚠️ Research Limitations

### What This System Cannot Do

1. **No live web search**: Only answers from uploaded papers
2. **No fine-tuning**: Uses general-purpose embeddings
3. **Limited reasoning**: Single-paper synthesis, not multi-paper
4. **Semantic chunking**: 512-token fixed chunks may fragment long sections

### External Dependencies

- **Google API**: Embedding and LLM generation (required)
- **PostgreSQL**: Vector store must be running (required)
- **arXiv/Semantic Scholar APIs** (optional, if enabled)

### Verification Assumptions

- Semantic similarity ≠ semantic correctness (embedding-based verification may miss subtle errors)
- Citation extraction is heuristic-based (some citations may be missed)
- No ground truth validation (system doesn't know if papers contain errors)

---

## 🔮 Research Directions (Future Work)

### High Priority
- **Hybrid Retrieval**: Combine semantic search (vectors) + keyword search (BM25)
- **Smart Chunking**: Intelligent segmentation by section/paragraph
- **Citation Ranking**: Prioritize by relevance and authority

### Medium Priority
- **Multi-Paper Synthesis**: Answer that synthesizes across papers
- **Literature Mapping**: Identify connections between papers
- **Temporal Analysis**: Track how ideas evolve across years

### Lower Priority (Exploratory)
- **Claim Extraction**: Automatically identify key claims in papers
- **Contradiction Detection**: Flag inconsistent findings
- **Meta-Analysis Support**: Assist in quantitative synthesis

---

## 🛠 Local Development

### Prerequisites
```bash
Docker Desktop          # For containerized services
Python 3.9+           # Backend runtime
Node.js 18+           # Frontend runtime
```

### Quick Start
```bash
# 1. Clone
git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git

# 2. Configure
cp .env.example .env
# Edit .env: GOOGLE_API_KEY, GROQ_API_KEY

# 3. Launch
docker-compose up --build

# 4. Verify
python demo_rag_test.py
```

### Access Points
```
Frontend:    http://localhost:5173
Backend API: http://localhost:8000/api/
Database:    localhost:5432
```

---

## ☁️ Deployment (Azure)

For production use, VeriRAG deploys on Azure Container Apps with Terraform IaC.

**Budget**: ~$97/month (PostgreSQL, Redis, Container Apps)

See [docs/deployment.md](docs/deployment.md) for setup.

---

## 📂 Project Structure

```
.
├── apps/
│   ├── backend/        # Django RAG engine
│   │   └── ai_engine/  # Core verification logic
│   └── frontend/       # React interface
├── docs/               # Technical documentation
├── tests/              # Evaluation tests
└── ops/                # Infrastructure (Terraform)
```

---

## 📚 Documentation

- **[RAG Pipeline](docs/rag_pipeline.md)**: Algorithm details and verification logic
- **[Evaluation Framework](docs/evaluation.md)**: Testing methodology and metrics
- **[Deployment Guide](docs/deployment.md)**: Azure setup and monitoring

---

## 📜 License & Citation

MIT License – see [LICENSE](LICENSE).

**For research use:**
```bibtex
@software{verirag2024,
  title={VeriRAG: Verified Research Assistant},
  author={Kumar, Vaibhav},
  year={2024},
  url={https://github.com/VaibhavKumar2005/cloud-native-ai-library-system}
}
```

---

## 🤝 Contributing

Contributions welcome in these areas:
- Improving retrieval quality
- Better verification methods
- Evaluation methodologies
- Documentation

Please open issues before submitting large PRs.

---

**Status**: Active Research Project | **License**: MIT
