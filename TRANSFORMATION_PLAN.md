# VeriRAG Product Transformation Plan
> From "Engineering Project" → "Funded Startup Product"

**Timeline:** 3-5 days  
**Effort:** ~40 hours  
**Risk:** LOW (all changes are UI/messaging, core RAG stays the same)  

---

## ⚡ QUICK WINS (Day 1 - 4 hours)

### 1. Update Landing Page Copy ✅
**File:** `apps/frontend/src/LandingPage.jsx`

**Changes:**
- Replace "Docker, Terraform, ACA-ready" with "Evidence First, Honest About Limits, Built for Research"
- Remove all infrastructure references
- Add "0 hallucinations," "100% cited answers," "<1¢ per query" metrics
- New CTA: "Start Asking Questions" (not "Enter Workspace")

**Impact:** Game-changer for first impression. Pitch now sounds like a product, not a DevOps tool.

---

### 2. Create Clean Answer Component ✅
**File:** `apps/frontend/src/components/ResearchGradeAnswer.jsx`

**Changes:**
- New component that shows:
  - Answer paragraph
  - Evidence list (source, page, excerpt)
  - Confidence bar (high=green, mid=yellow, low=red)
  - "View in PDF" button for each source
  - Rejection message (not an error, a feature)

**Import in Dashboard:**
```jsx
import ResearchGradeAnswer from '@/components/ResearchGradeAnswer'

// In your chat area:
<ResearchGradeAnswer 
  answer={response.answer}
  citations={response.citations}
  confidence={response.confidence}
  method={response.method}
/>
```

**Impact:** Users now see trust-building design instead of chat bubbles.

---

### 3. Create Clean RAG Core ✅
**File:** `apps/backend/ai_engine/core_rag.py`

**Changes:**
- New simplified query function
- Every function has ONE job
- Readable for external researchers
- Replaces complex `rag_logic.py` calls

**Use in views:**
```python
from ai_engine.core_rag import answer_academic_question

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def query_endpoint(request):
    result = answer_academic_question(
        query=request.data.get('query'),
        user_id=request.user.id
    )
    return Response(result)
```

**Impact:** Code is now understandable and copy-paste-able.

---

## 🎨 MEDIUM EFFORT (Day 2-3 - 12 hours)

### 4. Remove Ops Metrics from Dashboard
**File:** `apps/frontend/src/Dashboard.jsx`

**DELETE:**
```jsx
// ❌ Delete these sections:
<section>
  <AnimatedCounter value={0} suffix=" tokens" />
  <span>Processed by CostOps</span>
</section>

<section>
  <FaithfulnessGauge score={0.73} />
  <span>Last 100 interactions</span>
</section>

<section>
  <StatusDot ok={true} />
  <span>Redis: Active</span>
</section>

<section>
  NEXT ACTION
  Keep the workspace moving
</section>
```

**KEEP:**
- Document upload button
- Query history
- Document library list

**ADD:**
- "Quick tips" for common questions
- "Try asking:" suggestions

**Impact:** Dashboard now feels like a research tool, not a monitoring console.

---

### 5. Redesign Dashboard Layout
**New Layout:**
```
┌─────────────────────────────────────────────┐
│ VeriRAG Workspace                      [↗] │
├──────────────────┬─────────────────────────┤
│  QUERY AREA      │  EVIDENCE VIEWER        │
│  [Ask...]        │  [Answer + Citations]   │
│  [History >      │  [Confidence meter]     │
│                  │                         │
│  DOCUMENT LIST   │  [View PDF highlight]   │
│  - Paper A       │                         │
│  - Paper B       │                         │
└──────────────────┴─────────────────────────┘
```

**Code approach:**
```jsx
<div className="grid grid-cols-3 gap-6 h-screen">
  <div className="col-span-1 overflow-y-auto">
    <QueryPanel />
    <DocumentLibrary />
  </div>
  <div className="col-span-2">
    <EvidenceViewer />
  </div>
</div>
```

**Impact:** Users focus on questions + evidence, not metrics.

---

### 6. Update Auth/Login Page
**File:** `apps/frontend/src/LoginPage.jsx`

**Changes:**
- Remove "JWT today, OAuth-ready next"
- Add: "Secure login. Your documents stay private."
- Add: "Single sign-on with Google/GitHub coming soon"
- Keep the "no password, one-time link" flow

**Impact:** Trust messaging, not tech jargon.

---

## 🚀 HIGH IMPACT (Day 4-5 - 10 hours)

### 7. Add PDF Highlight Feature
**Concept:**
When user clicks "View in PDF" on a citation:
1. Load the PDF in a side panel
2. Highlight the cited excerpt
3. Show context (surrounding text)

**Implementation:**
```jsx
// New component
<PDFViewer
  pdfUrl={document.file_url}
  highlightText="RAG improves accuracy..."
  pageNumber={2}
/>
```

**Impact:** This is where trust happens. Seeing the actual text = confidence.

---

### 8. Add Query Suggestions
**Concept:**
When workspace is empty, show:
```
"Here are some questions you could ask once you upload a document:

• What are the main findings?
• Summarize the methodology
• What does this say about X?
• How does Y compare to Z?"
```

**Impact:** Guides new users. Increases engagement.

---

### 9. Create README for Funded-Startup Positioning
**File:** `README.md`

**New structure:**
```markdown
# VeriRAG

Ask questions. See the evidence. Trust the answer.

## Why VeriRAG?

- **Evidence-First**: Every answer shows sources + page numbers
- **Honest**: Rejects questions outside your document set
- **Fast**: <1¢ per query thanks to smart retrieval

## For Researchers, Built by Engineers

Tired of LLM hallucinations? Upload your papers. Ask anything.
VeriRAG grounds responses in your documents and shows you why.

## Quick Start

### 1. Upload PDFs
Click "Upload" and add your research papers.

### 2. Ask Questions
"What does Paper A say about RAG?" or "Compare methods in Papers A and B."

### 3. See Evidence
Click "View in PDF" to see the cited excerpt.

## Technical Foundation

- Vector search (pgvector)
- Multi-source synthesis
- Confidence scoring
- Field-level encryption

[See Architecture](docs/ARCHITECTURE.md)
```

**Impact:** Repositioning in 30 seconds.

---

## 🗑️ WHAT TO DELETE ENTIRELY

These are DISTRACTING and don't add product value:

| Component | File | Reason |
|-----------|------|--------|
| CostOps dashboard card | `Dashboard.jsx` | Users don't care about cost breakdown |
| Faithfulness gauge | `Dashboard.jsx` | Confidence number is enough |
| Service health dots | `Dashboard.jsx` | Ops metric, not user feature |
| Operational visibility section | `Dashboard.jsx` | Not product value |
| Docker/Terraform mentions | `LandingPage.jsx` | Infrastructure, not promise |
| "Worker + queue split" | `LandingPage.jsx` | Implementation detail |
| System insights API calls | `Dashboard.jsx` | If users don't see it, don't fetch it |

---

## 💾 WHAT TO KEEP (Core Value)

| Component | Why |
|-----------|-----|
| RAG query logic | **The heart.** Three-tier confidence system is brilliant. |
| pgvector retrieval | **Fast and works.** No reason to change. |
| Document upload | **User feature.** Keep the UX smooth. |
| Citations + confidence | **Trust signals.** Expand these. |
| JWT + encryption | **Security is table stakes.** Keep it. |
| Vault integration | **Good for enterprise.** Keep but hide from users. |

---

## 📊 WHAT TO ADD (High Impact, Low Effort)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| PDF highlight on citation | 4 hrs | 🔥🔥🔥 See the proof | P0 |
| Query suggestions | 2 hrs | 🔥🔥 New user engagement | P1 |
| Download citations as BibTeX | 3 hrs | 🔥🔥 Researcher workflow | P1 |
| Query history sidebar | 2 hrs | 🔥 UX polish | P2 |
| "Try example" button | 1 hr | 🔥 First-time value | P2 |

---

## 🧪 TESTING CHECKLIST (Before shipping)

- [ ] Landing page loads (no tech jargon in hero)
- [ ] Can upload a PDF
- [ ] Can ask a question
- [ ] Answer shows with citations
- [ ] Rejection message is helpful (not scary)
- [ ] Can click "View in PDF"
- [ ] Confidence bar displays correctly
- [ ] Mobile responsive (at least readable)
- [ ] No console errors
- [ ] Load time <2 sec

---

## 📅 DEPLOYMENT TIMELINE

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| Day 1 | Landing page copy + Answer component | Frontend | ✅ Ready |
| Day 1 | Core RAG simplification | Backend | ✅ Ready |
| Day 2 | Remove ops metrics from Dashboard | Frontend | → Start here |
| Day 2-3 | Dashboard redesign (grid layout) | Frontend | → Next |
| Day 3 | PDF highlight feature | Frontend | → Then |
| Day 4 | Query suggestions + polish | Frontend | → Then |
| Day 4-5 | Testing + bug fixes | QA | → Finally |

---

## 🎯 SUCCESS CRITERIA

By Day 5 you should be able to:

1. ✅ Show LandingPage to someone who doesn't code. They understand what it does.
2. ✅ Upload a real PDF (not sample_book.pdf)
3. ✅ Ask a real question ("What does this paper say about X?")
4. ✅ See answer with evidence
5. ✅ Click "View in PDF" and see the highlighted text
6. ✅ Push to production with confidence

---

## 🚀 FINAL DIFF SUMMARY

```diff
  LandingPage:
-  "Docker, Terraform, ACA-ready service split"
+  "Evidence-First, Honest, Built for Researchers"

  Dashboard:
-  CostOps gauge, Faithfulness meter, Service health dots
+  Clean query area + evidence viewer

  Answer Format:
-  Chat bubble ("The answer is...")
+  Research grade (Answer | Evidence | Confidence)

  Code:
-  Complex rag_logic.py calls
+  Clean core_rag.py functions

  Feel:
-  "Engineering project"
+  "Funded startup product"
```

---

## 🎓 WHAT MAKES THIS DIFFERENT

This isn't "adding more features."

This is **removing noise and amplifying signal.**

**Signal:** Evidence, citations, confidence, trust.  
**Noise:** Metrics, infrastructure, implementation details.

---

## Questions?

1. **"Won't I lose the ops monitoring?"**  
   → No. Keep it in Django admin. Users don't need it in the product.

2. **"What if users want to see cost per query?"**  
   → Add a /settings page later. Don't put it in the main dashboard.

3. **"Should I deploy gradually?"**  
   → Yes. Roll out changes over 2 features, not all at once.

4. **"What about analytics?"**  
   → Add Posthog/Mixpanel secretly. Don't show raw metrics to users.

---

**You've built an 80% product. This plan makes it a 95% product.**

Time to ship. 🚀
