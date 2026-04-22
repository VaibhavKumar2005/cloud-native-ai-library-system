# The VeriRAG Pitch Deck
*How to talk about this product like a funded startup*

---

## 🎯 THE PROBLEM (30 seconds)

Researchers ask LLMs questions about papers and get back:
- **Confident answers** with no sources
- **Hallucinated citations** that don't exist
- **No way to verify** if the answer is actually grounded

ChatGPT + research = guessing game.

---

## ✅ THE SOLUTION (30 seconds)

**VeriRAG**: Upload your PDFs. Ask anything. See the evidence.

Every answer shows:
- ✅ Which documents it came from
- ✅ Exact page numbers and excerpts
- ✅ Confidence score (we admit when we don't know)

Research without guessing.

---

## 🔬 WHY THIS MATTERS

### The Market
- 500M researchers globally
- Each spends ~10 hours/week searching papers
- Current tools: Google Scholar + manual reading

### The Pain
- LLMs are fast but untrustworthy  
- "Who said this?" takes 5 minutes of verification
- Institutional knowledge lives in PDFs, not databases

### The Opportunity
- $500M TAM (academic + enterprise search)
- PLG motion (start free → institutional license)
- Competitors asleep (no one solving this well)

---

## 💡 THE PRODUCT

### Core Differentiator: **Evidence-First Design**

| Feature | VeriRAG | ChatGPT | Perplexity |
|---------|---------|---------|-----------|
| Shows sources | ✅ Exact page | ❌ Just links | ✅ Links |
| Admits limits | ✅ Rejects bad Qs | ❌ Hallucinates | ❌ Hallucinates |
| PDF highlight | ✅ Click → see text | ❌ No | ❌ No |
| Cost per query | ✅ <1¢ | N/A | ❌ $0.05+ |
| Private docs | ✅ Encrypted | ❌ OpenAI has it | ❌ Cloud |

---

## 🏗️ HOW IT WORKS

```
1. User uploads: "my_paper.pdf"
   ↓
2. System indexes 50 chunks into pgvector
   ↓
3. User asks: "What's the main finding?"
   ↓
4. Three-tier confidence check:
   • 0.88+? Return chunk directly ($0)
   • 0.70-0.88? Synthesize with LLM ($0.001)
   • <0.70? Reject ("Not in your docs")
   ↓
5. Show answer + citations + confidence
```

**Economics:** 3-tier logic cuts LLM costs by 70%.

---

## 👥 WHO USES IT

### Primary: PhD Students & Academic Researchers
- **Pain:** Manually verify 100+ papers per thesis
- **Gain:** 10x faster literature review
- **Budget:** Not much, but will pay for institutional access

### Secondary: Enterprise Researchers
- Legal discovery teams
- Medical researchers
- Compliance teams
- **Budget:** $100k+/year

### Tertiary: Knowledge Workers
- Anyone with 100+ PDFs
- Consultants, analysts, archivists
- **Budget:** $50-200/month

---

## 📈 THE METRICS THAT MATTER

### Right Now (Before shipping v2)
- 0 hallucinations in test queries
- 100% of answers are cited
- <100ms query latency

### After shipping (Q2 2025)
- Target: 1000 beta users
- Target: 50% of uploaded docs get queried  
- Target: <$0.50 cost per active user per month

---

## 💰 THE Business Model

### FREE TIER
- 10 documents
- 100 queries/month
- Access for 30 days

### PRO ($10/mo)
- 100 documents
- Unlimited queries
- Priority support

### ENTERPRISE (Custom)
- Unlimited documents
- Private deployment option
- SSO + audit logs
- Dedicated support
- **Target ACV:** $100k+

---

## 🚀 WHY NOW?

1. **LLMs are commodity**: Claude/GPT are commodities. The value is now in interface + trust.
2. **Vector DBs are ready**: pgvector + embedding models make this feasible at scale.
3. **Hallucination is problem #1**: Every AI product now needs "evidence layer."
4. **No competitor shipping this**: Perplexity focuses on web search. No one owns "document search + verification."

---

## 🎨 THE DESIGN PHILOSOPHY

### NOT: Engineering Dashboard
```
CostOps Tokens: 0
Faithfulness Score: 72%
Service Health: ✅ Active
```

### YES: Researcher Experience
```
Answer:
RAG improves accuracy by grounding responses...

Evidence:
📄 Smith et al. (2020) - Page 2
"RAG combines retrieval with generation..."
[View in PDF]

Confidence: 91% (Synthesized from 3 sources)
```

---

## 📊 TRACTION

### What we've built:
- ✅ Full RAG pipeline
- ✅ pgvector integration (fast)
- ✅ Three-tier confidence system
- ✅ Encryption at rest
- ✅ Multi-tenant architecture
- ✅ Real UI (not mock)

### What's left:
- Polish answer formatting (3 hours)
- PDF highlight feature (4 hours)
- Landing page repositioning (2 hours)
- Beta user testing (1 week)

**Timeline to beta:** 1 week

---

## 🎯 MILESTONES

| When | What | Target |
|------|------|--------|
| End of April | Ship v1 + landing page | 100 beta signups |
| May | PDF highlight + API | 500 users |
| June | PDF upload from web | 1000 active users |
| July | Enterprise features | $50k MRR |

---

## 🧠 WHY THIS WINS

### vs Competitors:
- **Perplexity**: Makes search better. We make researchers' *own documents* searchable.
- **ChatGPT pro**: Generic chat. We're specialized + verifiable.
- **Semantic Scholar**: No interactive Q&A. We do.
- **Academic search engines**: Expensive. We're cheap.

### Our moat:
1. Trust brand (first product known for "no hallucinations")
2. Researcher community (network effects)
3. Institutional adoption path (sales motion exists)

---

## 💻 THE TECH STACK (Why it matters)

| Component | Choice | Why |
|-----------|--------|-----|
| Vector DB | pgvector | Fast, cheap, no vendor lock |
| Embeddings | text-embedding-3-small | $0.02 per million tokens |
| Synthesis | GPT-3.5-turbo or open models | Cost + speed + quality |
| Frontend | React + Vite | Fast, polished, familiar |
| Backend | Django + DRF | Battle-tested, scalable |
| Hosting | Azure Container Apps | Cloud-native, multi-tenant |
| Security | Vault + field encryption | Enterprise-ready |

All decisions are "boring but right" - no hype.

---

## 🎓 THE ASK

**Seed round: $1.2M**

Use of funds:
- Product engineering: 50% ($600k)
- Go-to-market: 25% ($300k)
- Operations: 15% ($180k)
- Runway: 10% ($120k)

Exit path: **Acquire** or **IPO path** in 5-7 years.

---

## ❓ FAQ FOR INVESTORS

**Q: "Isn't this just Pinecone + OpenAI?"**  
A: No. Pinecone is infrastructure. We're a consumer product with trust brand. Different moat.

**Q: "Won't OpenAI add this?"**  
A: Maybe. But they're horizontal. We're vertical + specialized. Like git vs GitHub.

**Q: "Why documents and not web search?"**  
A: Lower CAC, higher retention. Researchers own their documents forever.

**Q: "What's your unit economics?"**  
A: $50 CAC, $15/mo ARPU (Pro tier), 36-month payback on enterprise.

---

## 🏁 THE CLOSE

> **VeriRAG isn't another AI product.**
> 
> **It's the answer layer for people who care about answers being true.**

Research without guessing. Evidence before confidence. Trust over hype.

That's the product. That's the company.

---

*Pitch delivered at demo day.* 🚀
