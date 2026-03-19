# CI/CD Pipeline Consolidation Summary

## 🎯 What Changed

### Before (7 Workflows) ❌
- `ci.yml` — Frontend + backend tests
- `ci-cd.yml` — Full pipeline
- `deploy-aca.yml` — Manual deployment
- `simple-deploy.yml` — Simplified deploy
- `backend-security.yml` — Trivy scans
- `frontend-security.yml` — Frontend security
- `security-remediation-check.yml` — Remediation tracking

**Problem:** Confusing, overlapping, hard to maintain

### After (1 Workflow) ✅
- `.github/workflows/deploy.yml` — Unified CI/CD pipeline

**Benefit:** Single source of truth, clear flow, portfolio-ready

---

## 📊 New Workflow Architecture

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 Code Push or Pull Request                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  STAGE 1: Validate Env      │
         │  - Check secrets/variables  │
         │  - Generate image tag       │
         │  - Determine if deploy      │
         └──────────────┬──────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
    ┌──────────────┐          ┌──────────────┐
    │  STAGE 2:    │          │  STAGE 3:    │
    │  Test        │          │  Security    │
    │  - Django    │          │  - Trivy     │
    │  - Frontend  │          │  - SARIF     │
    └──────────────┘          └──────────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
    ┌─ If main branch & success ─┐
    │                             │
    ▼                             ▼
┌──────────────┐          ┌──────────────┐
│  STAGE 4:    │          │  STAGE 5:    │
│  Build/Push  │          │  Deploy to   │
│  - Docker    │          │  ACA         │
│  - ACR       │          │  - Health    │
└──────────────┘          └──────────────┘
```

---

## 🚀 When it Runs

### Pull Request to `main`
✅ Tests run
✅ Security scans run
❌ **No deployment** (safe preview)

### Push to `main` (merge)
✅ Tests run
✅ Security scans run
✅ Docker build & push to ACR
✅ **Auto-deploy to Azure Container Apps**

### Manual trigger
✅ All stages (useful for troubleshooting)

---

## 📦 Job Breakdown

### 1. **Validate** (~1 min)
- Generate short SHA for image tags
- Check if deployment should run (main branch only)
- Verify all required Azure variables are set
- **Output**: `should-deploy` flag for later jobs

### 2. **Test** (~15 min)
- **Backend**:
  - Python 3.11 setup
  - Install requirements.txt
  - Django system checks
  - Database migrations
  - Unit tests (ai_engine, librarian, verifier)
- **Frontend**:
  - Node.js 20 setup
  - Install dependencies
  - Build with Vite
  - Lint with ESLint

### 3. **Security** (~10 min)
- Trivy scan backend dependencies
- Trivy scan frontend dependencies
- Upload to GitHub Security tab (SARIF format)
- Store artifacts for 90 days

### 4. **Build & Push** (~20 min)
**Only runs on merge to main**
- Docker Buildx multi-platform
- Build backend image
- Build frontend image (with VITE_API_URL)
- Push to Azure Container Registry
- Tag with both `latest` and short SHA

### 5. **Deploy** (~15 min)
**Only runs on merge to main**
- Azure login via OIDC (no secrets needed!)
- Update backend container app
- Update frontend container app
- Optional: Update celery worker
- Health check verification

---

## 🔐 Security Features

✅ **OIDC Authentication** (no secrets in code!)
✅ **Least privilege** (only pushes/deploys on main)
✅ **Artifact retention** (90 days for audit trail)
✅ **SARIF reporting** (GitHub Security integration)
✅ **Environment protection** (production deployment requires approval if configured)

---

## 🛠 What You Need to Set Up

### GitHub Secrets (encrypted)
```
AZURE_CLIENT_ID          # From Azure AD app registration
AZURE_TENANT_ID          # Your Azure tenant ID
AZURE_SUBSCRIPTION_ID    # Your subscription ID
```

### GitHub Variables (public)
```
AZURE_RESOURCE_GROUP     # e.g., rg-verirag-dev
BACKEND_APP_NAME         # e.g., aca-verirag-backend
FRONTEND_APP_NAME        # e.g., aca-verirag-frontend
CELERY_APP_NAME          # (optional, can be empty)
VITE_API_URL             # e.g., https://api.verirag.dev
```

---

## 📝 Next Steps

1. **Archive old workflows** (keep as reference):
   ```bash
   # Don't delete, just move to archive
   mkdir .github/workflows/archive-old-workflows
   mv .github/workflows/ci.yml .github/workflows/archive-old-workflows/
   ```

2. **Test the new workflow:**
   - Create a PR to `main` (should run tests only)
   - See if all jobs pass
   - Merge PR (should deploy)

3. **Verify deployment:**
   - Check Azure Container Apps portal
   - Verify new images in ACR
   - Test health endpoints

4. **Clean up** (after confirming it works):
   - Delete archived workflows
   - Update team documentation

---

## 💡 Why This is Better for Your Portfolio

✅ **Single workflow** = easier to understand
✅ **Clear stages** = shows DevOps thinking
✅ **Conditional deployment** = demonstrates best practices
✅ **Security scanning** = shows you care about quality
✅ **OIDC auth** = modern Azure practices
✅ **Good job naming** = self-documenting code

**Verdict**: This is **interview-ready** 🎯

---

## 🐛 Troubleshooting

### Deployment won't run
- ✅ Check if push is to `main` branch
- ✅ Verify all GitHub secrets/variables are set
- ✅ Check `validate` job output

### Tests failing
- ✅ See the test logs in GitHub Actions
- ✅ Check if PostgreSQL service is healthy
- ✅ Verify Django settings in CI environment variables

### Security scan issues
- ✅ SARIF upload failures are non-blocking (continue-on-error: true)
- ✅ Check GitHub Security tab for details
- ✅ Fix vulnerabilities in requirements.txt/package.json

### ACR push failing
- ✅ Verify Azure login succeeded
- ✅ Check ACR name is correct
- ✅ Ensure service principal has ACR push role

---

## 📚 Related Files

- **Deployment guide**: `docs/guides/ACA_DEPLOYMENT.md`
- **Environment variables**: `docs/guides/ACA_DEPLOYMENT_ENV.md`
- **Local testing**: `LOCAL_TESTING_VALIDATION_GUIDE.md`

