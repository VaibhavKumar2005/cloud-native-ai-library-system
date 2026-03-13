# GitHub Actions CI/CD Setup Guide

This guide explains how to set up GitHub Actions for VeriRAG using automatic CI and manual Azure Container Apps deployment.

## 🎯 Pipeline Overview

The workflow setup now does this:
1. **CI on push/PR** - Runs backend tests, frontend build validation, and Docker build checks
2. **Manual deployment** - Builds images, pushes them to your chosen registry, and updates Azure Container Apps only when you trigger it

## 📋 Prerequisites

Before the workflows can run, you need:
- Azure subscription with Container Apps already deployed
- Azure Service Principal with Container Apps permissions
- A container registry account:
  - GitHub Container Registry (`ghcr.io`) recommended for showcase cost control
  - Docker Hub also works
  - ACR can still be used later without changing the app architecture

## 🔐 Required GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

### 1. Registry Secrets

**What**: Credentials used by the manual deploy workflow to push images.

**Recommended setup for GHCR**:
- Create a Personal Access Token with `write:packages`
- Use your GitHub username as the registry username

**Add to GitHub secrets**:
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`

### 2. AZURE_CREDENTIALS

**What**: Service Principal JSON for Azure CLI authentication

**How to create**:
```powershell
# Login to Azure
az login

# Create Service Principal with Container Apps permissions
az ad sp create-for-rbac `
  --name "github-actions-verirag" `
  --role "Contributor" `
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-verirag-dev `
  --sdk-auth

# Copy the entire JSON output
```

**Output format**:
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

**Add to GitHub**:
- Name: `AZURE_CREDENTIALS`
- Value: `<paste-entire-json>`

## ⚙️ Configuration Variables

Go to: **Settings → Secrets and variables → Actions → Variables tab**

### Required Repository Variables

Go to: **Settings → Secrets and variables → Actions → Variables tab**

- `AZURE_RESOURCE_GROUP`
- `BACKEND_APP_NAME`
- `CELERY_APP_NAME`
- `FRONTEND_APP_NAME`

### Optional Repository Variables

- `REGISTRY_SERVER`
  - Default is `ghcr.io`
  - Set to `docker.io` if you want Docker Hub
  - Set to your ACR login server later if you migrate
- `IMAGE_NAMESPACE`
  - For GHCR: usually your GitHub username or org
  - For Docker Hub: your Docker Hub namespace
- `VITE_API_URL`

**What**: Frontend API endpoint (optional, defaults to https://api.verirag.dev)

**Add if needed**:
- Name: `VITE_API_URL`
- Value: Your custom backend URL

## 🚀 How the Pipeline Works

## Workflow Structure

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
  - Runs automatically on push to `main` or `develop`
  - Runs automatically on pull requests to `main`
  - Does not deploy anything

- [`.github/workflows/deploy-aca.yml`](../.github/workflows/deploy-aca.yml)
  - Runs only on `workflow_dispatch`
  - Builds images from the selected ref
  - Pushes images to your configured registry
  - Updates ACA manually

### Trigger Events

**Main branch push**:
```bash
git add .
git commit -m "feat: add new feature"
git push origin main
```

This runs CI only.

**Develop branch push**:
```bash
git checkout -b develop
git push origin develop
```

This also runs CI only.

**Pull Request**:
```bash
gh pr create --base main --head feature-branch
```

This runs CI only.

**Manual deploy**:
1. Open the **Actions** tab
2. Select `VeriRAG Manual ACA Deploy`
3. Choose the `git_ref`
4. Trigger the workflow

### Workflow Steps

#### 1. Test Stage
- Sets up PostgreSQL with pgvector
- Runs Django unit tests
- Validates frontend build

#### 2. Manual Build & Push Stage
- Generates git short SHA as image tag
- Builds Docker images when you explicitly deploy
- Pushes to the registry you configured

#### 3. Manual Deploy Stage
- Logs into Azure using Service Principal
- Updates backend ACA app
- Updates Celery worker ACA app
- Updates frontend ACA app
- Performs backend health check on `/api/health/`
- Publishes deployment summary

## 📊 Monitoring Pipeline Runs

### View Workflow Status
1. Go to **Actions** tab in GitHub
2. Click on latest workflow run
3. View detailed logs for each job

### Check Deployment Status
```powershell
# List recent deployments
az containerapp revision list \
  --name ca-verirag-dev-backend \
  --resource-group rg-verirag-dev \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime}" \
  --output table

# View logs
az containerapp logs show \
  --name ca-verirag-dev-backend \
  --resource-group rg-verirag-dev \
  --follow
```

## 🎓 Best Practices for Academic Evaluation

### Meaningful Commits
✅ **Good**:
```bash
git commit -m "feat: add dual-agent verification with faithfulness scoring

- Implemented Generator Agent using Gemini 2.0 Flash
- Added Critic Agent for hallucination detection
- Integrated faithfulness scoring (0-1 scale)
- Added comprehensive test coverage

Closes #12"
```

❌ **Bad**:
```bash
git commit -m "update"
git commit -m "fix stuff"
```

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Build/CI changes

### Regular Activity
- **Commit frequency**: Multiple meaningful commits per week
- **Branch strategy**: Use feature branches, create PRs
- **Code review**: Review team member PRs, leave constructive comments
- **Documentation**: Update README, add code comments

### Pull Request Best Practices
1. **Create descriptive PRs**:
   ```markdown
   ## Changes
   - Added JWT authentication with auto-refresh
   - Fixed Vault connection issues
   - Updated models to Gemini 2.0 Flash
   
   ## Testing
   - All 11 API tests pass
   - Verified locally with docker-compose
   
   ## Screenshots
   [Add relevant screenshots]
   ```

2. **Respond to feedback promptly**:
   - Within 24 hours
   - Ask clarifying questions
   - Make requested changes
   - Mark conversations as resolved

3. **Use draft PRs** for work-in-progress:
   ```bash
   gh pr create --draft --title "WIP: Add observability features"
   ```

## 🔧 Troubleshooting

### Pipeline Fails on Docker Push
**Error**: `denied: requested access to the resource is denied`

**Fix**: Check that `REGISTRY_USERNAME` and `REGISTRY_PASSWORD` are set correctly and that the token can push to your chosen registry.

### Azure Deployment Fails
**Error**: `az: command not found` or authentication error

**Fix**: Verify `AZURE_CREDENTIALS` contains valid Service Principal JSON

### Health Check Fails
**Error**: Health check returns 000 or 500

**Fix**: 
1. Check Azure Container Apps logs
2. Verify environment variables are set in Container Apps
3. Allow 2-3 minutes for cold start on first deployment

### Security Scan Blocks Deployment
**Action**: Review findings in **Security → Code scanning**

**Options**:
- Fix critical vulnerabilities and recommit
- Mark as false positive with justification
- Add to ignore list with reason

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Container Registry Documentation](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Container Apps CI/CD](https://learn.microsoft.com/en-us/azure/container-apps/github-actions)
- [Conventional Commits](https://www.conventionalcommits.org/)

## 🎯 Quick Start Checklist

- [ ] Add `REGISTRY_USERNAME` to GitHub Secrets
- [ ] Add `REGISTRY_PASSWORD` to GitHub Secrets
- [ ] Add `AZURE_RESOURCE_GROUP`, `BACKEND_APP_NAME`, `CELERY_APP_NAME`, and `FRONTEND_APP_NAME` to repository variables
- [ ] Add `AZURE_CREDENTIALS` to GitHub Secrets
- [ ] Deploy infrastructure using `infrastructure/deploy.ps1`
- [ ] Add API keys using `infrastructure/add-api-keys.ps1`
- [ ] Make a test commit and push to trigger pipeline
- [ ] Verify workflow succeeds in Actions tab
- [ ] Check deployment at backend URL
- [ ] Review security scan results

**Questions?** Open an issue or contact the team.
