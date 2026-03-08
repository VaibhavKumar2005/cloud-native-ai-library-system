# Quick Rebuild & Test Guide

## After Security Fixes

This guide provides quick commands to rebuild and verify the security-patched containers.

## Prerequisites

- Docker Desktop running
- Working directory: project root (`Azure Cloud Native RAG/`)
- Terminal: PowerShell or Bash

---

## 1. Rebuild Images

### Option A: Build Individual Services

```powershell
# Frontend
cd frontend
docker build -t verirag-frontend:secure .
cd ..

# Backend
cd backend
docker build -t verirag-backend:secure .
cd ..
```

### Option B: Build All Services via Docker Compose

```powershell
# Build all services (recommended)
docker-compose build --no-cache

# Or rebuild and start all services
docker-compose up --build -d
```

---

## 2. Verify Builds Succeeded

```powershell
# List built images
docker images | Select-String verirag

# Expected output:
# verirag-frontend   secure   ...
# verirag-backend    secure   ...
```

---

## 3. Scan with Trivy (Optional but Recommended)

### Install Trivy (if not already installed)

```powershell
# Windows (Chocolatey)
choco install trivy

# Or download from: https://github.com/aquasecurity/trivy/releases
```

### Scan Images

```powershell
# Scan frontend (only HIGH and CRITICAL)
trivy image --severity HIGH,CRITICAL verirag-frontend:secure

# Scan backend (only HIGH and CRITICAL)
trivy image --severity HIGH,CRITICAL verirag-backend:secure

# Full scan with all severities
trivy image verirag-frontend:secure
trivy image verirag-backend:secure
```

### Expected Results
- Significantly fewer (or zero) HIGH/CRITICAL vulnerabilities
- OS packages should be up-to-date
- Python dependencies (Django, gunicorn, etc.) should show patched versions

---

## 4. Test Locally

### Start All Services

```powershell
# Start with security-patched images
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### Run API Tests

```powershell
# Test backend health
./test-api.ps1

# Or manually test
curl http://localhost:8000/api/health/
# Expected: {"status": "healthy"}

# Test frontend
curl http://localhost:8080/
# Expected: HTML response
```

### Check Logs

```powershell
# Backend logs
docker-compose logs rag-backend

# Celery worker logs
docker-compose logs rag-celery-worker

# Frontend logs
docker-compose logs -f rag-frontend  # if added to compose
```

---

## 5. Run Full Test Suite

```powershell
# Backend Django tests
docker-compose exec rag-backend python manage.py test

# Or from host (if .venv activated)
cd backend
pytest
```

---

## 6. Push to Registry (After Verification)

Once verified, push the patched images:

```powershell
# Tag for your registry (Docker Hub or ACR)
docker tag verirag-frontend:secure vaibhavkumar0412/verirag-frontend:latest
docker tag verirag-backend:secure vaibhavkumar0412/verirag-backend:latest

# Login to registry
docker login  # Docker Hub
# Or
az acr login --name yourregistry  # Azure Container Registry

# Push images
docker push vaibhavkumar0412/verirag-frontend:latest
docker push vaibhavkumar0412/verirag-backend:latest
```

---

## 7. Trigger CI/CD (Recommended)

Instead of manually pushing, commit and push changes to trigger automated builds:

```powershell
# Stage all security fixes
git add frontend/Dockerfile backend/Dockerfile backend/requirements.txt
git add SECURITY_SCANNING.md SECURITY_REMEDIATION.md REBUILD_GUIDE.md

# Commit with clear message
git commit -m "security: remediate Trivy CVEs - upgrade base images and Python deps

- Frontend: Upgraded to nginx:stable-alpine + apk upgrade
- Backend: Added apt-get upgrade to Debian stages
- Python: Upgraded Django 5.0.2→5.1.7+, gunicorn 21.2.0→23.0.0+
- Added security scanning documentation

Fixes: #116, #103, #102, #132, #125, #124, #123-#68 (OS CVEs)
Fixes: #6, #2, #1, #16-#3 (Django CVEs)
Fixes: #24, #23 (gunicorn CVE-2024-1135)
Fixes: #43, #42 (wheel CVE-2024-38335)
Fixes: #25 (jaraco.context CVE-2024-6345)"

# Push to trigger CI/CD
git push origin main
```

GitHub Actions will:
1. Run tests
2. Build patched images
3. Push to Azure Container Registry
4. Deploy to Azure Container Apps (if configured)

---

## 8. Monitor GitHub Security Tab

After CI/CD completes:

1. Go to: `https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/security/code-scanning`
2. Check that Trivy alerts are resolved or significantly reduced
3. If new scans are configured in CI, wait for Trivy action results

---

## Troubleshooting

### Build Fails: "node:20-alpine not found"
```powershell
# Pull base images explicitly
docker pull node:20-alpine
docker pull nginx:stable-alpine
docker pull python:3.11-slim
```

### Build Fails: "No matching distribution found for Django>=5.1.7"
This might happen if pip doesn't have the latest version. Update pip in the Dockerfile or use a specific version:
```dockerfile
RUN pip install --upgrade pip setuptools wheel
```

### Trivy Still Shows HIGH Vulnerabilities
- Ensure you rebuilt with `--no-cache` flag
- Check that base images were actually upgraded
- Some vulnerabilities may be in dependencies of dependencies (harder to fix)

### Application Not Starting After Upgrade
- Check Django 5.1 compatibility: https://docs.djangoproject.com/en/5.1/releases/5.1/
- Check logs: `docker-compose logs rag-backend`
- Verify migrations: `docker-compose exec rag-backend python manage.py showmigrations`

---

## Quick Reference: Dockerfile Changes

### Frontend: What Changed
```diff
- FROM nginx:1.25-alpine AS runtime
+ FROM nginx:stable-alpine AS runtime
+ RUN apk update && apk upgrade --no-cache
```

### Backend: What Changed
```diff
- RUN apt-get update && apt-get install -y --no-install-recommends \
+ RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
```

### Requirements.txt: What Changed
```diff
- Django==5.0.2
+ Django>=5.1.7
- gunicorn==21.2.0
+ gunicorn>=23.0.0
+ wheel>=0.46.0
+ jaraco.context>=6.0.0
```

---

## Next Steps

1. ✅ Rebuild images  
2. ✅ Scan with Trivy  
3. ✅ Test locally  
4. ✅ Push to Git / trigger CI/CD  
5. ⏳ Monitor GitHub Security tab  
6. ⏳ Deploy to production  

---

## Resources

- Full scanning guide: `SECURITY_SCANNING.md`
- Detailed remediation report: `SECURITY_REMEDIATION.md`
- Trivy documentation: https://aquasecurity.github.io/trivy/
- Django 5.1 release notes: https://docs.djangoproject.com/en/5.1/releases/5.1/

---

**Last Updated**: March 2026  
**Maintainer**: DevSecOps Team
