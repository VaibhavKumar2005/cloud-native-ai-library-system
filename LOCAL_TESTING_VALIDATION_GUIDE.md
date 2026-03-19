# 🧪 Local Testing & CI/CD Validation Guide

## ⚠️ Potential Breaking Points (What We'll Check)

### Backend Risks
- [ ] Missing Python dependencies (cryptography, langchain_openai)
- [ ] Import errors in new encryption code
- [ ] Database migration issues with new fields
- [ ] Changes to existing views/models breaking existing code
- [ ] Signal handler interfering with gunicorn

### Frontend Risks
- [ ] Build errors from new imports
- [ ] Runtime errors in new components
- [ ] Color system not being imported correctly
- [ ] EmailAuthForm component not exporting properly
- [ ] CSS compilation issues with new styles

### Integration Risks
- [ ] API endpoints not matching frontend expectations
- [ ] CORS issues between frontend/backend
- [ ] Environment variables not set correctly
- [ ] Docker build failures
- [ ] Volume mount issues

### CI/CD Pipeline Risks
- [ ] Linting failures (ESLint, Flake8)
- [ ] Type checking failures
- [ ] Missing dependencies in requirements.txt
- [ ] Docker image build timeouts
- [ ] Database migrations failing
- [ ] Tests failing (if any exist)

---

## 📋 Test Plan (Sequential Order)

### PHASE 1: Frontend Validation (10 minutes)
```bash
Step 1.1: Verify no import errors
Step 1.2: Check linted code
Step 1.3: Build production bundle
Step 1.4: Run dev server and check UI
```

### PHASE 2: Backend Validation (15 minutes)
```bash
Step 2.1: Check Python syntax
Step 2.2: Verify imports work
Step 2.3: Run migrations (test database)
Step 2.4: Start backend server
```

### PHASE 3: Docker Validation (20 minutes)
```bash
Step 3.1: Build backend Docker image
Step 3.2: Build frontend Docker image
Step 3.3: Start docker-compose
Step 3.4: Test API health endpoint
Step 3.5: Test email auth endpoint
```

### PHASE 4: Full Stack Integration (15 minutes)
```bash
Step 4.1: Frontend can reach backend API
Step 4.2: Email auth flow works
Step 4.3: OAuth flow works
Step 4.4: No console errors in browser
Step 4.5: Database encryption works
```

### PHASE 5: CI/CD Readiness (10 minutes)
```bash
Step 5.1: All dependencies in requirements.txt
Step 5.2: All dependencies in package.json
Step 5.3: Dockerfile builds without errors
Step 5.4: No linting errors
Step 5.5: No security vulnerabilities
```

---

## 🔍 DETAILED TEST COMMANDS

### PHASE 1: Frontend Validation

#### Step 1.1: Verify No Import Errors
```bash
# Check if Login.jsx has all imports
cd apps/frontend
grep -E "^import" src/Login.jsx

Expected output:
✅ import { useEffect, useState } from "react";
✅ import { useNavigate } from "react-router-dom";
✅ import { Card, CardContent } from "@/components/ui/card";
✅ import { Button } from "@/components/ui/button";
✅ import EmailAuthForm from "@/components/EmailAuthForm";
✅ import { colors } from "@/lib/colors";
```

#### Step 1.2: Check ESLint
```bash
cd apps/frontend
npx eslint src/Login.jsx src/components/EmailAuthForm.jsx src/lib/colors.js

Expected: ✅ 0 errors, 0 warnings
```

#### Step 1.3: Production Build
```bash
cd apps/frontend
npm run build

Expected Output:
✅ ✓ 1872 modules transformed
✅ ✓ built in X.XXs
✅ No errors
```

#### Step 1.4: Dev Server
```bash
cd apps/frontend
npm run dev

Expected:
✅ VITE v7.3.1 ready in XXX ms
✅ ➜  Local: http://localhost:5173/
✅ Navigate to http://localhost:5173 in browser
✅ See login page with:
   - VeriRAG logo
   - "Enterprise AI Research Platform" text
   - Email input form
   - Google button
   - GitHub button
   - Security features list
   - No console errors (F12 DevTools)
```

---

### PHASE 2: Backend Validation

#### Step 2.1: Check Python Syntax
```bash
cd apps/backend
python -m py_compile ai_engine/models.py
python -m py_compile rag_backend/auth_views.py
python -m py_compile rag_backend/wsgi.py

Expected: ✅ No output = syntax OK
```

#### Step 2.2: Verify Imports Work
```bash
cd apps/backend

# Test import of encryption code
python -c "from ai_engine.models import Document; print('✅ Document import OK')"

# Test import of signal handler
python -c "import rag_backend.wsgi; print('✅ WSGI import OK')"

# Test cryptography availability
python -c "from cryptography.fernet import Fernet; print('✅ Cryptography available')"

Expected: ✅ All three print success messages
```

#### Step 2.3: Check Requirements
```bash
cd apps/backend

# Verify cryptography is in requirements
grep -i "cryptography" requirements.txt

Expected: ✅ cryptography>=40.0.0 (or similar version)

# Test installing requirements (in venv)
pip install -r requirements.txt

Expected: ✅ Successfully installed X packages
```

#### Step 2.4: Database Migrations
```bash
cd apps/backend

# This will FAIL if database not running, that's OK
python manage.py migrate --dry-run

OR (if database running in Docker)

docker-compose up -d rag-db
python manage.py migrate

Expected: ✅ OK migrations applied (or "No migrations to apply")
```

---

### PHASE 3: Docker Validation

#### Step 3.1: Build Backend Image
```bash
cd /path/to/Azure\ Cloud\ Native\ RAG

docker build --no-cache \
  -f apps/backend/Dockerfile \
  -t verirag-backend:test .

Expected Output (at end):
✅ => => exporting to image
✅ => => naming to docker.io/library/verirag-backend:test
✅ Successfully tagged verirag-backend:test

If fails:
❌ "ModuleNotFoundError: langchain_openai" = Known issue, needs pip install
❌ "FROM base as runtime" error = Dockerfile syntax issue
```

#### Step 3.2: Build Frontend Image
```bash
docker build --no-cache \
  -f apps/frontend/Dockerfile \
  -t verirag-frontend:test .

Expected: ✅ Successfully built
```

#### Step 3.3: Start Docker Compose
```bash
# Stop any running containers first
docker-compose down

# Start fresh
docker-compose up -d

# Wait 30 seconds
sleep 30

# Check status
docker-compose ps

Expected Status:
✅ rag-db: RUNNING (healthy)
✅ rag-redis: RUNNING (healthy)
✅ rag-vault: RUNNING (healthy)
✅ rag-frontend: RUNNING (healthy)
✅ rag-backend: RUNNING (or failed - will check logs)
```

#### Step 3.4: Test API Health
```bash
# Wait for backend to be ready
sleep 10

curl http://localhost:8000/api/health/

Expected Response (200 OK):
{
  "healthy": true,
  "timestamp": "2026-03-19T...",
  "version": "2.0.0"
}

If fails:
- Check docker logs: docker-compose logs rag-backend
- Most likely: langchain_openai missing
```

#### Step 3.5: Test Email Auth Endpoint
```bash
curl -X POST http://localhost:8000/api/auth/email/send/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

Expected Response (200 OK):
{
  "status": "link_sent",
  "email": "test@example.com",
  "message": "Magic link sent to test@example.com...",
  "magic_link": "http://localhost:5173/login?email_token=..."
}

If fails:
- Check error message in response
- Check backend logs: docker-compose logs rag-backend
```

---

### PHASE 4: Full Stack Integration

#### Step 4.1: Frontend Can Reach Backend
```bash
# In browser DevTools, run:
fetch('http://localhost:8000/api/health/')
  .then(r => r.json())
  .then(d => console.log('✅ Backend reached:', d))

Expected: ✅ Console shows health check response
```

#### Step 4.2: Email Auth Flow (Manual)
```bash
# In browser (http://localhost:5173):
1. See login page ✅
2. Enter email: test@example.com ✅
3. Click "Send Magic Link" ✅
4. See success message "Check your email" ✅
5. No console errors ✅
```

#### Step 4.3: OAuth Flow (Manual)
```bash
# In browser:
1. Click "Continue with Google"
2. Popup opens ✅
3. Or redirects to Google ✅
4. (don't complete, just verify flow starts)

# Similarly for GitHub
```

#### Step 4.4: Browser Console Check
```bash
# Open DevTools (F12)
# Go to Console tab
# Look for:
❌ ANY red errors
❌ "Failed to fetch"
❌ "Cannot read property"
✅ Should be clean or only CORS warnings (OK for now)
```

#### Step 4.5: Encryption Code Works
```bash
# In Docker container backend:
docker-compose exec rag-backend python manage.py shell

# Then in Python shell:
from ai_engine.models import Document
from django.contrib.auth.models import User

# Test user
user = User.objects.first()

# Test encryption methods exist
print(Document._derive_user_key(1))  # Should return key bytes
print("✅ Encryption methods available")
```

---

### PHASE 5: CI/CD Readiness Checks

#### Step 5.1: Check requirements.txt
```bash
cd apps/backend

# Verify all needed packages
grep -E "cryptography|langchain|django|celery|redis" requirements.txt

Expected: ✅ All should be present with versions
```

#### Step 5.2: Check package.json
```bash
cd apps/frontend

# Verify all dependencies
npm list react react-router-dom axios lucide-react

Expected: ✅ All versions listed, no errors
```

#### Step 5.3: Run Linters
```bash
# Python linting (if available)
cd apps/backend
flake8 ai_engine/models.py --max-line-length=120
# Or check for syntax
python -m py_compile $(find . -name "*.py")

# JavaScript linting
cd apps/frontend
npm run lint

Expected: ✅ Zero errors (or acceptable warnings)
```

#### Step 5.4: Check for Security Issues
```bash
# Python security
cd apps/backend
pip install bandit
bandit -r ai_engine/models.py rag_backend/auth_views.py

# JavaScript security
cd apps/frontend
npm audit

Expected: ✅ No critical vulnerabilities
```

---

## 🎯 CRITICAL BREAKING POINTS TO WATCH

### 1. Missing Dependencies ⚠️
```
PROBLEM: langchain_openai not in Docker
IMPACT: ❌ Backend won't start
SOLUTION: Already in requirements.txt, Docker cache issue
FIX: docker build --no-cache
```

### 2. Import Errors ⚠️
```
PROBLEM: from cryptography.fernet import Fernet fails
IMPACT: ❌ models.py won't load
SOLUTION: cryptography>=40.0.0 in requirements.txt
VERIFY: pip install cryptography
```

### 3. Database Migration ⚠️
```
PROBLEM: New fields (encrypted_content, is_encrypted) cause migration error
IMPACT: ❌ Database initialization fails
SOLUTION: Django auto-creates migration
VERIFY: python manage.py makemigrations
```

### 4. CORS Issues ⚠️
```
PROBLEM: Frontend at :5173 can't reach Backend at :8000
IMPACT: ⚠️ Email auth endpoint fails
SOLUTION: CORS settings in Django settings.py
VERIFY: Check CORS_ALLOWED_ORIGINS points to http://localhost:5173
```

### 5. Frontend Build Failures ⚠️
```
PROBLEM: Vite build fails due to missing @ alias
IMPACT: ❌ npm run build fails
SOLUTION: jsconfig.json has paths configured
VERIFY: npm run build succeeds
```

### 6. Signal Handler Conflicts ⚠️
```
PROBLEM: Signal handler in wsgi.py conflicts with gunicorn
IMPACT: ⚠️ Graceful shutdown might not work
SOLUTION: Already tested pattern, shouldn't break anything
VERIFY: Monitor container shutdown in Docker
```

---

## ✅ SUCCESS CRITERIA

### Phase 1 (Frontend)
```
✅ npm run build succeeds (0 errors)
✅ npm run dev starts without errors
✅ Browser shows login page
✅ ESLint: 0 errors
```

### Phase 2 (Backend)
```
✅ Python syntax check passes
✅ All imports work (cryptography, django, etc)
✅ Encryption methods exist and callable
✅ requirements.txt complete
```

### Phase 3 (Docker)
```
✅ Docker build succeeds
✅ docker-compose up -d succeeds
✅ All services healthy
✅ Backend is running (not error state)
```

### Phase 4 (Integration)
```
✅ Frontend loads at :5173
✅ Backend responds to /api/health/
✅ Email auth endpoint works (200 response)
✅ No CORS errors in console
```

### Phase 5 (CI/CD)
```
✅ All dependencies in requirements/package.json
✅ Linting shows 0 errors
✅ No security vulnerabilities (critical)
✅ Dockerfile builds cleanly
```

---

## 🚨 WHAT TO DO IF IT BREAKS

| Breaking Point | Error | Fix |
|---|---|---|
| Frontend build | `Module not found` | Check @ alias in jsconfig.json |
| Frontend build | `CSS error` | Run npm install again |
| Backend import | `ModuleNotFoundError` | pip install -r requirements.txt |
| Docker build | `langchain_openai` | Already in requirements.txt, cache issue |
| API health | `Connection refused` | Backend crashed, check logs |
| API health | `404 Not Found` | Wrong URL, should be /api/health/ |
| Email endpoint | `400 Bad Request` | Invalid JSON or missing email field |
| Docker startup | Container exits | Check logs: docker-compose logs rag-backend |

---

## 📊 Test Execution Checklist

```
PHASE 1: FRONTEND
  [ ] 1.1 Verify imports
  [ ] 1.2 Run ESLint
  [ ] 1.3 Production build
  [ ] 1.4 Dev server starts

PHASE 2: BACKEND
  [ ] 2.1 Python syntax
  [ ] 2.2 Imports work
  [ ] 2.3 Requirements complete
  [ ] 2.4 Migrations run

PHASE 3: DOCKER
  [ ] 3.1 Backend image builds
  [ ] 3.2 Frontend image builds
  [ ] 3.3 docker-compose up succeeds
  [ ] 3.4 Health endpoint works
  [ ] 3.5 Email endpoint works

PHASE 4: INTEGRATION
  [ ] 4.1 Frontend → Backend connectivity
  [ ] 4.2 Email auth manual test
  [ ] 4.3 OAuth manual test
  [ ] 4.4 Browser console clean
  [ ] 4.5 Encryption code works

PHASE 5: CI/CD
  [ ] 5.1 All backend dependencies
  [ ] 5.2 All frontend dependencies
  [ ] 5.3 Linting passes
  [ ] 5.4 No security issues
  [ ] 5.5 Docker ready
```

---

## 🎯 Expected Total Time

```
Phase 1: 10 minutes (frontend)
Phase 2: 15 minutes (backend)
Phase 3: 25 minutes (docker, with waits)
Phase 4: 15 minutes (integration)
Phase 5: 10 minutes (CI/CD checks)

TOTAL: ~75 minutes for complete validation
```

---

## 🚀 Ready to Test?

Say **"Start Phase 1"** when ready, and I'll guide you through each step with real commands to run!
