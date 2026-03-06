# PDF Upload & Vector Embedding Test Guide

## 🎯 Quick Diagnosis Steps

### Step 1: Run Comprehensive Test Suite
```powershell
.\test-pdf-pipeline.ps1
```

This will test all 8 components of the pipeline and show you exactly where the failure occurs.

---

## 🔍 Manual Testing (Step-by-Step)

### Test 1: Backend API is Running
```powershell
curl http://localhost:8000/api/health/
```

**Expected:** `{"healthy": true, "services": {...}}`

**If fails:** Run `docker-compose up -d`

---

### Test 2: Initialize Vault with API Keys
```powershell
.\init_vault.ps1
```

**Required:** You need:
- GOOGLE_API_KEY (from https://aistudio.google.com/apikey)
- GROQ_API_KEY (from https://console.groq.com/)

**If skipped:** PDF processing will fail with `GOOGLE_API_KEY is missing`

---

### Test 3: Check Vault Contains Secrets
```powershell
docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault kv get -mount=secret myapp
```

**Expected:** Should show GOOGLE_API_KEY and GROQ_API_KEY entries

---

### Test 4: Create Test User
```powershell
docker exec -it rag-backend python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: admin123
```

---

### Test 5: Upload PDF via curl
```powershell
# Get JWT token
$loginPayload = @{username="admin"; password="admin123"} | ConvertTo-Json
$token = (Invoke-RestMethod -Uri "http://localhost:8000/api/token/" -Method Post -Body $loginPayload -ContentType "application/json").access

# Upload test PDF
$headers = @{Authorization="Bearer $token"}
Invoke-RestMethod -Uri "http://localhost:8000/api/documents/" -Method Post -Headers $headers -Form @{
    title="Test PDF"
    file=Get-Item "test.pdf"
}
```

**Expected:** Returns `{"id": 1, "title": "Test PDF", ...}`

---

### Test 6: Watch Celery Worker Process the PDF
```powershell
docker logs -f rag-celery-worker
```

**Expected to see:**
- `Received task: ai_engine.tasks.on_document_uploaded`
- `Ingesting document ID X`
- `✅ Document Y successfully ingested (N chunks)`

**Common errors:**
- `GOOGLE_API_KEY is missing` → Run `.\init_vault.ps1`
- `File not found at /app/media/documents/` → Volume mapping issue (already fixed)
- `ImportError: google.generativeai` → Already fixed (migrated to google-genai)

---

### Test 7: Check Document is Marked as Processed
```powershell
docker exec rag-backend python manage.py shell
```

```python
from ai_engine.models import Document
docs = Document.objects.all()
for doc in docs:
    print(f"ID: {doc.id}, Title: {doc.title}, Processed: {doc.processed}")
```

**Expected:** `Processed: True`

---

### Test 8: Verify Vector Embeddings in Database
```powershell
docker exec rag-db psql -U admin -d verirag_db -c "SELECT COUNT(*) FROM langchain_pg_embedding;"
```

**Expected:** Non-zero count (e.g., 15 chunks from your PDF)

**If 0:** Embeddings were not created. Check:
1. Vault has GOOGLE_API_KEY
2. Celery worker processed without errors

---

### Test 9: Query the RAG System
```powershell
$queryPayload = @{query="What is cloud computing?"} | ConvertTo-Json
$headers = @{Authorization="Bearer $token"; "Content-Type"="application/json"}

Invoke-RestMethod -Uri "http://localhost:8000/api/query/" -Method Post -Headers $headers -Body $queryPayload
```

**Expected:**
```json
{
  "answer": "Based on the documents...",
  "verification": "verified",
  "context": [...],
  "model_used": "gemini-1.5-flash"
}
```

---

## 🐛 Common Issues & Fixes

### Issue 1: "Failed to load PDF" on Frontend
**Cause:** Frontend not connected to backend

**Fix:**
```powershell
cd frontend
npm install
npm run dev
```

Then check `src/App.jsx` for the API URL:
```javascript
const API_URL = "http://localhost:8000/api"
```

---

### Issue 2: "GOOGLE_API_KEY is missing"
**Cause:** Vault not initialized

**Fix:**
```powershell
.\init_vault.ps1
```

---

### Issue 3: PDF uploads but never gets processed
**Cause:** Celery worker not receiving tasks

**Check:**
```powershell
# Check Redis connection
docker exec rag-redis redis-cli ping  # Should return PONG

# Check Celery is connected
docker logs rag-celery-worker | Select-String "Connected to redis"
```

**Fix:**
```powershell
docker-compose restart rag-celery-worker
```

---

### Issue 4: 401 Unauthorized on API calls
**Cause:** Missing or expired JWT token

**Fix:**
1. Get new token:
```powershell
$login = @{username="admin"; password="admin123"} | ConvertTo-Json
$token = (Invoke-RestMethod -Uri "http://localhost:8000/api/token/" -Method Post -Body $login -ContentType "application/json").access
```

2. Use in requests:
```powershell
$headers = @{Authorization="Bearer $token"}
```

---

### Issue 5: CORS errors in browser console
**Cause:** Frontend running on different port

**Fix:** Update `.env`:
```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Then restart backend:
```powershell
docker-compose restart rag-backend
```

---

## 📊 Full Diagnostic Commands

```powershell
# 1. Check all containers
docker-compose ps

# 2. Backend logs
docker logs rag-backend --tail 50

# 3. Celery worker logs
docker logs rag-celery-worker --tail 50

# 4. Check database documents
docker exec rag-backend python manage.py shell -c "from ai_engine.models import Document; print(Document.objects.all())"

# 5. Check vector embeddings
docker exec rag-db psql -U admin -d verirag_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"

# 6. Check Vault status
docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault status
```

---

## ✅ Expected Working Flow

1. **Upload PDF** → Backend saves to `/app/media/documents/`
2. **Celery receives task** → `on_document_uploaded` task queued
3. **Worker processes** → Loads PDF, chunks text, creates embeddings
4. **Embeddings stored** → PGVector stores in `langchain_pg_embedding` table
5. **Document marked processed** → `Document.processed = True`
6. **Query works** → Semantic search returns relevant chunks + LLM answer

---

## 🚀 Quick Fix Script

If nothing works, reset everything:

```powershell
# Stop all containers
docker-compose down -v

# Remove old volume data (⚠️ deletes all data)
docker volume rm azurecloudnativerag_postgres_data
docker volume rm azurecloudnativerag_celerybeat_schedule

# Rebuild and start
docker-compose up -d --build

# Wait 30 seconds
Start-Sleep -Seconds 30

# Initialize Vault
.\init_vault.ps1

# Create superuser
docker exec -it rag-backend python manage.py migrate
docker exec -it rag-backend python manage.py createsuperuser

# Run test suite
.\test-pdf-pipeline.ps1
```

---

**Need more help?** Run `.\test-pdf-pipeline.ps1` first and share the output!
