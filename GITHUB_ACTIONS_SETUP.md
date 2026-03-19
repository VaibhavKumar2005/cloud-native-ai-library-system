# GitHub Actions Setup Checklist

## Quick Start: Make Your Pipeline Work

### ✅ Step 1: Add GitHub Secrets

Go to: **Settings → Secrets and variables → Actions → Secrets** on your GitHub repo

Add these **encrypted** secrets (obtained from Azure):

```
AZURE_CLIENT_ID          = ce3d23c1-c364-41e5-998c-e1d3cf4691b1
AZURE_TENANT_ID          = cb90253c-15cb-48c4-b59c-d902b127637d
AZURE_SUBSCRIPTION_ID    = b7d6d48a-9b60-420c-b046-1e1512b81243
```

> ⚠️ **Important**: These look like real values from your feedback, but verify they match your actual Azure registration!

---

### ✅ Step 2: Add GitHub Variables

Go to: **Settings → Secrets and variables → Actions → Variables** on your GitHub repo

Add these **public** variables:

```
AZURE_RESOURCE_GROUP     = rg-verirag-dev
BACKEND_APP_NAME         = aca-verirag-backend
FRONTEND_APP_NAME        = aca-verirag-frontend
CELERY_APP_NAME          = aca-verirag-celery-worker
VITE_API_URL             = https://backend.verirag.dev
```

> 💡 Adjust these to match your actual Azure Container App names

---

### ✅ Step 3: Verify Azure OIDC Setup

Your Azure app registration must have **Federated Credentials** configured:

**GitHub Organization**: `https://token.actions.githubusercontent.com`
**Repository**: `VaibhavKumar2005/cloud-native-ai-library-system`
**Branch**: `main`

The file `apps/backend/oidc_cred.json` already shows the config, but verify in Azure portal:
- Go to Azure AD → App registrations
- Select your app
- Click **Certificates & secrets → Federated credentials**
- Verify GitHub-VeriRAG OIDC trust exists

---

### ✅ Step 4: Test the Pipeline

1. **Create a test branch**:
   ```bash
   git checkout -b test/ci-pipeline
   ```

2. **Make a small change** (e.g., update README):
   ```bash
   echo "# Test PR" >> TEST.md
   git add TEST.md
   git commit -m "test: trigger CI pipeline"
   git push origin test/ci-pipeline
   ```

3. **Create Pull Request** to `main`
   - Watch GitHub Actions tab
   - Should run: validate → test → security
   - Should **NOT** deploy (PR, not merge)

4. **If all jobs pass**, merge the PR
   - Watch GitHub Actions again
   - Should now run: validate → test → security → build-push → deploy
   - Verify images appear in Azure Container Registry
   - Verify containers restart in Azure Container Apps

---

## 📋 Configuration Reference

### Required Secrets
| Secret | Description | Example |
|--------|-------------|---------|
| `AZURE_CLIENT_ID` | Service principal client ID | `ce3d23c1-c364-41e5-998c-e1d3cf4691b1` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `cb90253c-15cb-48c4-b59c-d902b127637d` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `b7d6d48a-9b60-420c-b046-1e1512b81243` |

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_RESOURCE_GROUP` | Resource group name | `rg-verirag-dev` |
| `BACKEND_APP_NAME` | Backend container app name | `aca-verirag-backend` |
| `FRONTEND_APP_NAME` | Frontend container app name | `aca-verirag-frontend` |
| `CELERY_APP_NAME` | Worker app (optional) | `aca-verirag-celery-worker` |
| `VITE_API_URL` | Frontend API endpoint | `https://backend.verirag.dev` |

### Optional Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `ACR_REGISTRY` | Azure Container Registry | `acrvaibhavrag2026.azurecr.io` |
| `ACR_REPOSITORY` | Repository prefix | `verirag` |
| `LOCATION` | Azure region | `eastus` |

---

## 🔍 Debugging Failed Runs

### Pipeline shows "Error: Unrecognized Azure scope" or "not authorized"
```
❌ Cause: AZURE_CLIENT_ID, AZURE_TENANT_ID, or AZURE_SUBSCRIPTION_ID is wrong
✅ Fix: Double-check your Azure secrets in GitHub
```

### Docker build fails with "failed to solve"
```
❌ Cause: Missing requirements.txt or package.json
✅ Fix: Verify files exist at apps/backend/requirements.txt and apps/frontend/package.json
```

### Deployment times out
```
❌ Cause: Azure Container Apps are slow to update
✅ Fix: Normal, may take 3-5 minutes. Check Azure portal for status
```

### Health check fails after deploy
```
❌ Cause: API endpoint not responding
✅ Fix: Check if backend is running: az containerapp logs show -n aca-verirag-backend -g rg-verirag-dev
```

---

## 📊 Monitoring Your Pipeline

### Live view
- Go to repo → **Actions** tab
- Click active workflow run
- Watch jobs execute in real-time

### Results
- **Successful PR**: Shows ✅ on PR checks
- **Successful merge**: Shows ✅ and updates container apps
- **Failure**: Shows ❌ with error logs

### Job Summary
Each job shows a **summary** at the end with status, times, and deployment details

---

## 🎯 Best Practices

1. **Always test PRs first** (don't merge without passing tests)
2. **Monitor security scans** (fix CRITICAL/HIGH severity issues)
3. **Keep secrets rotated** (Azure recommends every 90 days)
4. **Archive old workflows** (don't delete, helps with git history)
5. **Use `workflow_dispatch`** (manual trigger for emergency deploys)

---

## 🚀 Once Everything Works

You can now confidently say:

> "I have a fully automated CI/CD pipeline from GitHub to Azure Container Apps. Every push to main automatically runs tests, security scans, builds Docker images, pushes to Azure Container Registry, and deploys to production."

That's **enterprise-level DevOps** on your resume! 🎓

