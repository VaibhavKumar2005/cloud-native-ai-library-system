# 🚀 VeriRAG - Quick Reference Card

## One-Click Launch

### Windows (Easiest)
```batch
double-click: docker-launch.bat
```

### PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File docker-launch.ps1
```

### Manual
```powershell
docker-compose up -d
```

---

## Access Your System

| What | URL | Purpose |
|------|-----|---------|
| Frontend | http://localhost:5173 | Upload papers & ask questions |
| Backend | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger documentation |

---

## Test Search Functions

```powershell
# Search arXiv
curl -X POST http://localhost:8000/api/search/arxiv/ `
  -H "Content-Type: application/json" `
  -d '{"query":"RAG", "max_results":10}'

# Search Patents
curl -X POST http://localhost:8000/api/search/patents/ `
  -H "Content-Type: application/json" `
  -d '{"query":"machine learning", "max_results":10}'

# Search Everything
curl -X POST http://localhost:8000/api/search/all/ `
  -H "Content-Type: application/json" `
  -d '{"query":"neural networks", "sources":["arxiv","semantic_scholar","patents"]}'
```

---

## Verify System Works

```powershell
python test_rag_quick.py
```

This tests:
- ✅ Backend responding
- ✅ Frontend loaded
- ✅ Database connected
- ✅ 7 sample queries working

---

## Evaluate Your System

Read: `RAG_EVALUATION_FRAMEWORK.md`

Then test these queries:
```
1. "What is RAG?" → Should find papers
2. "How does RAG reduce hallucination?" → Should synthesize
3. "Explain turboquant" → Should search web
4. "Compare RAG vs fine-tuning" → Should compare
5-9. See framework for advanced tests
```

Score on 5 criteria:
- Context Relevance (0-10)
- Context Sufficiency (0-10)
- Answer Correctness (0-10)
- Groundedness (0-10)
- Hallucination Rate (0-10)

---

## Key Commands

```powershell
# View logs
docker-compose logs -f rag-backend

# Stop services
docker-compose down

# Stop & reset database
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Access database
docker exec -it rag-db psql -U admin -d verirag_db

# Create superuser
docker exec -it rag-backend python manage.py createsuperuser
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| **GETTING_STARTED.md** | Complete getting started (START HERE) |
| **RAG_EVALUATION_FRAMEWORK.md** | Evaluation methodology & test queries |
| **ARXIV_PATENTS_INTEGRATION.md** | Web search API reference |
| **DOCKER_SETUP.md** | Docker troubleshooting |
| **SETUP_COMPLETE.md** | What was created & why |

---

## 3-Day Plan

### Day 1: Evaluate
- Launch system
- Test 9 queries
- Score on 5 criteria
- Get baseline metrics

### Day 2: Improve
- Fix weak areas
- Better retrievals
- Improve citations
- Test patents

### Day 3: Deploy
- Polish UI
- Add features
- Deploy to Azure
- Document

---

## New Features You Have

✨ **arXiv Integration**
- 650k+ academic papers
- Free, no API key needed
- Real-time search

✨ **Patent Search**
- 10M+ USPTO patents
- Google Patents
- Inventor & assignee info

✨ **Semantic Scholar**
- 190M+ papers
- Citation counts
- Influential citations

✨ **Hybrid RAG**
- Local doc search first
- Web search fallback (if confidence < 0.7)
- Blended results with citations

✨ **Evaluation Framework**
- 5 core metrics
- 9 test queries
- Manual evaluation template
- Claude assessment prompts

---

## Success Indicators

✅ System is working when:
- Frontend loads
- Backend responds
- Queries return grounded answers
- Citations are accurate
- No hallucinations
- Confidence scores match accuracy

---

## Troubleshooting

### Docker won't start
```
1. Install Docker: https://www.docker.com/products/docker-desktop/
2. Start Docker Desktop
3. Wait 60 seconds
4. Run: docker ps
```

### Backend not responding
```
Wait 30 seconds - services are initializing
Run: docker-compose ps  # Check health status
```

### Port already in use
```
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Tests fail
```
docker-compose logs rag-backend
# Check for error messages
```

---

## API Endpoints

```
POST   /api/search/arxiv/           → Search arXiv
GET    /api/search/arxiv-latest/    → Latest by category
POST   /api/search/papers/          → Arχiv + Semantic Scholar
POST   /api/search/patents/         → Patents
POST   /api/search/all/             → Everything
POST   /api/search/augment-rag/     → Web fallback
```

---

## Remember

This system is **designed for evaluation**.

Use the framework to:
1. **Measure** current performance
2. **Identify** weak points
3. **Improve** specific areas
4. **Re-measure** improvements
5. **Document** results

---

## You're Ready! 🎉

Everything is set up. Time to:
1. Launch: `docker-compose up -d`
2. Test: `python test_rag_quick.py`
3. Evaluate: Read `RAG_EVALUATION_FRAMEWORK.md`
4. Improve: Implement fixes from evaluation
5. Deploy: Use azure-prepare skill (optional)

Good luck! 🚀
