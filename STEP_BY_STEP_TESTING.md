# TIER 1 Implementation - Step-by-Step Execution Guide

## Phase 1: Verify Changes (No running required)

### Step 1.1: Check Frontend Changes
```bash
cd apps/frontend

# Verify key files exist
ls -la src/lib/colors.js                    # ✅ Should exist (updated)
ls -la src/Login.jsx                        # ✅ Should exist (rebuilt)
ls -la src/components/EmailAuthForm.jsx     # ✅ Should exist (new)
cat src/Login.jsx | head -20                # Verify imports updated
```

**Expected Output:**
- Login.jsx imports: `EmailAuthForm`, `colors` (not `EmailAuthTab`)
- EmailAuthForm.jsx exists with email form logic
- colors.js has Azure Blue (#0078D4) as primary

### Step 1.2: Check Backend Changes
```bash
cd apps/backend

# Verify key files
ls -la rag_backend/auth_views.py            # ✅ Has email endpoints
ls -la rag_backend/wsgi.py                  # ✅ Has signal handling
ls -la Dockerfile                           # ✅ Has STOPSIGNAL
grep -n "class EmailLoginToken" ai_engine/models.py  # ✅ Model exists
```

**Expected Output:**
- EmailLoginToken model defined in models.py (should see class definition)
- STOPSIGNAL SIGTERM in Dockerfile
- Signal handler for SIGTERM in wsgi.py

### Step 1.3: Verify Documentation
```bash
# Check deployment guide created
ls -la docs/guides/ACA_DEPLOYMENT.md        # ✅ Should exist
wc -l docs/guides/ACA_DEPLOYMENT.md         # Should be ~400+ lines
```

---

## Phase 2: Local Testing (Without Docker)

### Step 2.1: Install Frontend Dependencies
```bash
# From repo root
cd apps/frontend

# Check if node_modules exists
ls node_modules/ | wc -l              # If > 100, already installed
# If not:
npm install

# Verify key packages
npm list react react-router-dom axios lucide-react
```

**Expected:** All packages installed successfully

### Step 2.2: Start Frontend Dev Server
```bash
# From apps/frontend
npm run dev

# Output should show:
# VITE v... ready in XXX ms
# ➜  Local:   http://localhost:5173/
# ➜  press h to show help
```

✅ **Keep this running in terminal 1**

### Step 2.3: Check Frontend Loads
```bash
# In another terminal, test the frontend
curl http://localhost:5173/

# Should return HTML (not 404)
# Open browser: http://localhost:5173
# You should see the VeriRAG login page
```

---

## Phase 3: Backend Testing (Docker Required)

### Step 3.1: Start Docker Services
```bash
# From repo root
docker-compose up -d

# Wait 30 seconds for services to start
sleep 30

# Check status
docker-compose ps

# Expected output:
# NAME                COMMAND                  STATUS
# postgres            postgres                 Up (healthy)
# redis               redis-server             Up (healthy)
# backend             gunicorn rag_backend...  Up (healthy)
```

### Step 3.2: Test Health Endpoint
```bash
# Check backend is responding
curl http://localhost:8000/api/health/

# Expected response:
# {
#   "healthy": true,
#   "timestamp": "2026-03-18T...",
#   "version": "2.0.0"
# }
```

### Step 3.3: Test Email Auth Endpoint (Send)
```bash
# Send magic link request
curl -X POST http://localhost:8000/api/auth/email/send/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Expected response:
# {
#   "status": "link_sent",
#   "email": "test@example.com",
#   "message": "Magic link sent to test@example.com. Valid for 15 minutes.",
#   "magic_link": "http://localhost:5173/login?email_token=..."
# }

# ✅ If you see "magic_link" in response (DEBUG mode), copy the full token
TOKEN="<copy-the-token-from-magic_link-URL-parameter>"
```

### Step 3.4: Test Email Auth Endpoint (Verify)
```bash
# Get token from previous step output
TOKEN="<paste-token-from-step-3.3>"

# Verify the token
curl -X POST http://localhost:8000/api/auth/email/verify/ \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"${TOKEN}\"}"

# Expected response:
# {
#   "access": "eyJ0eXAiOiJKV1QiLC...",   # JWT token
#   "refresh": "eyJ0eXAiOiJKV1QiLC...",
#   "user": {
#     "id": 1,
#     "username": "test",
#     "email": "test@example.com"
#   }
# }

# ✅ If you got this, email auth works!
```

### Step 3.5: Test OAuth Endpoints (Still Work?)
```bash
# Get available providers
curl http://localhost:8000/api/auth/providers/

# Expected: JSON showing google, github, and other providers
# "enabled": true for each

# ✅ OAuth endpoints unchanged
```

---

## Phase 4: Frontend + Backend Integration

### Step 4.1: Test Login Page UI
```
Open browser: http://localhost:5173/login

Visual checklist:
✅ VeriRAG logo visible
✅ "Email or Magic Link" section visible (no tabs!)
✅ Email input field shown
✅ "Send Magic Link" button visible (BLUE color)
✅ Divider "or continue with" visible
✅ Google button visible
✅ GitHub button visible
✅ Mobile responsive (try resizing to 375px width)
```

### Step 4.2: Test Email Form on Frontend
```
In browser at http://localhost:5173/login:

1. Type email: "test2@example.com"
2. Click "Send Magic Link" button
3. Expected: Loading spinner, then success message
   "Check your email for a login link. Valid for 15 minutes."
4. ✅ Button should show back "Send another link" option
```

### Step 4.3: Test Login with Email Token (Manual)
```bash
# Step 1: Send magic link (get token from response)
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/email/send/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test3@example.com"}')

echo $RESPONSE

# Copy the magic_link URL (in DEBUG mode)
# Extract token: token_value_from_URL

# Step 2: Simulate clicking email link
# In browser, navigate to:
# http://localhost:5173/login?email_token=<TOKEN_FROM_STEP_1>

# Expected: Browser redirects to /app (dashboard)
# ✅ If you see dashboard, email auth complete flow works!
```

### Step 4.4: Test Google/GitHub OAuth (Visual Only)
```
In browser at http://localhost:5173/login:

1. Click "Sign in with Google" button
   - Expected: OAuth popup/redirect

2. Click "Sign in with GitHub" button
   - Expected: OAuth popup/redirect

✅ These should still work (unchanged from existing implementation)
```

---

## Phase 5: Docker Build Test

### Step 5.1: Build Backend Image
```bash
cd apps/backend

# Build
docker build -t verirag-backend:test .

# Expected: Build completes with no errors
# Last line should show: "Successfully tagged verirag-backend:test"

# Verify it builds
docker images | grep verirag-backend
```

### Step 5.2: Test Container Startup
```bash
# Run the built image
docker run --rm \
  -e DJANGO_SECRET_KEY="test-secret" \
  -e DATABASE_URL="postgresql://..." \
  -p 8000:8000 \
  verirag-backend:test

# Expected: No errors, gunicorn starts
# Last line: "[PID] Listening at: http://0.0.0.0:8000"
```

---

## Phase 6: Summary & Next Steps

### What's Working?

```
✅ Email Magic Link Auth
   - Backend: /api/auth/email/send/ generates tokens
   - Backend: /api/auth/email/verify/ verifies tokens & issues JWT
   - Frontend: Email form visible & functional
   - Full flow: Send → Check email → Click link → Login

✅ OAuth Systems (Unchanged)
   - Google OAuth: Still functional
   - GitHub OAuth: Still functional
   - Same JWT session as email auth

✅ UI/UX
   - Login page unified (no tabs)
   - Azure Blue colors applied (#0078D4)
   - Mobile responsive
   - Professional appearance

✅ Infrastructure
   - Dockerfile ACA-optimized
   - Signal handling for graceful shutdown
   - Health checks comprehensive
   - Documentation complete
```

### Troubleshooting During Testing

**Email endpoint returns 400 "Valid email address is required"**
```bash
# Check email format
curl -X POST http://localhost:8000/api/auth/email/send/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@domain.com"}'  # ← Make sure @ and . present
```

**"magic_link" not in response**
```bash
# Check DEBUG mode
curl http://localhost:8000/api/health/ | grep -i deploy
# If DEPLOY_MODE=cloud, magic_link hidden (security)
# That's OK - in production, link sent via email service
```

**Frontend won't load**
```bash
# Check if frontend dev server running
ps aux | grep "vite"
# If not: cd apps/frontend && npm run dev
```

**OAuth buttons don't work**
```bash
# Check if FRONTEND_URL set correctly
echo $FRONTEND_URL
# Should be http://localhost:5173 for local dev
# Set if not: export FRONTEND_URL=http://localhost:5173
```

---

## Ready to Deploy to ACA?

Once all tests above pass, follow: `docs/guides/ACA_DEPLOYMENT.md`

**Quick deploy checklist:**
1. Create Azure resources (PostgreSQL, Redis, Key Vault)
2. Build & push image to Azure Container Registry
3. Create Container App
4. Set environment variables
5. Run migrations
6. Test health endpoint
7. Done! 🚀

---

## Command Reference (Copy-Paste Ready)

```bash
# Full test sequence (run in order)

# Terminal 1: Frontend
cd apps/frontend && npm run dev

# Terminal 2: Backend + Tests
cd apps/backend
docker-compose up -d
sleep 30

# Test health
curl http://localhost:8000/api/health/

# Test email send
curl -X POST http://localhost:8000/api/auth/email/send/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Build docker image
docker build -t verirag-backend:test .

# Open browser
# http://localhost:5173/login  ← Test frontend
```

---

## When All Tests Pass ✅

Comment in the next message:

```
✅ Phase 1: Verified changes
✅ Phase 2: Frontend loads at localhost:5173
✅ Phase 3: Backend health check passes
✅ Phase 3: Email auth send works
✅ Phase 3: Email auth verify works
✅ Phase 4: Login page UI correct
✅ Phase 4: Email form submits
✅ Phase 5: Docker builds successfully
```

Then I'll help you deploy to Azure! 🚀
