# GitHub Actions CI/CD Setup Guide

This guide explains how to set up automated CI/CD for VeriRAG using GitHub Actions, Azure Container Registry (ACR), and Azure Container Apps.

## 🎯 Pipeline Overview

The CI/CD pipeline automatically:
1. **Tests** - Runs Django tests and frontend build validation
2. **Builds** - Creates optimized Docker images
3. **Pushes** - Publishes to Azure Container Registry with versioned tags
4. **Deploys** - Updates Azure Container Apps with new images
5. **Scans** - Performs security vulnerability scanning

## 📋 Prerequisites

Before the pipeline can run, you need:
 ✅ Azure Container Registry (ACR) deployed
- ✅ Azure subscription with Container Apps deployed
- ✅ Azure Service Principal with Container Apps permissions

## 🔐 Required GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

### 1. ACR Secrets (Registry Access)

**What**: Credentials to push images to your private Azure Container Registry.

**How to get**:
```powershell
# Get ACR Login Server
az acr show --name <your-acr-name> --resource-group rg-verirag-dev --query loginServer --output tsv

# Enable Admin User (if not enabled)
az acr update --name <your-acr-name> --admin-enabled true

# Get Username & Password
az acr credential show --name <your-acr-name>
```

**Add to GitHub**:
- Name: `ACR_LOGIN_SERVER`
- Value: (e.g., `veriragregistry.azurecr.io`)
- Name: `ACR_USERNAME`
- Value: (from `az acr credential show`)
- Name: `ACR_PASSWORD`
- Value: (from `az acr credential show`)

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

### Optional: VITE_API_URL

**What**: Frontend API endpoint (optional, defaults to https://api.verirag.dev)

**Add if needed**:
- Name: `VITE_API_URL`
- Value: Your custom backend URL

## 🚀 How the Pipeline Works

### Trigger Events

**Main branch push** (production deployment):
```bash
git add .
git commit -m "feat: add new feature"
git push origin main
```

**Develop branch push** (builds images, no deployment):
```bash
git checkout -b develop
git push origin develop
```

**Pull Request** (runs tests only):
```bash
gh pr create --base main --head feature-branch
```

### Workflow Steps

#### 1. Test Stage
- Sets up PostgreSQL with pgvector
- Runs Django unit tests
- Validates frontend build

#### 2. Build & Push Stage
- Generates git short SHA as image tag (e.g., `a1b2c3d`)
- Builds Docker images with build cache optimization
- Pushes to Azure Container Registry:
  - `<acr-name>.azurecr.io/verirag-backend:a1b2c3d`
  - `<acr-name>.azurecr.io/verirag-backend:latest`
  - `<acr-name>.azurecr.io/verirag-frontend:a1b2c3d`
  - `<acr-name>.azurecr.io/verirag-frontend:latest`

#### 3. Deploy Stage (Main branch only)
- Logs into Azure using Service Principal
- Updates backend Container App with new image
- Updates Celery worker Container App with new image
- Performs health check on `/api/health/`
- Generates deployment summary

#### 4. Security Scan Stage
- Runs Trivy vulnerability scanner
- Scans for CRITICAL and HIGH severity issues
- Uploads results to GitHub Security tab

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

### GitHub Security Alerts
- View security findings: **Security → Code scanning alerts**
- Trivy reports appear automatically after each deployment

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

**Fix**: Check that `ACR_USERNAME` and `ACR_PASSWORD` secrets are set correctly in GitHub.

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

- [ ] Add `ACR_LOGIN_SERVER` to GitHub Secrets
- [ ] Add `ACR_USERNAME` to GitHub Secrets
- [ ] Add `ACR_PASSWORD` to GitHub Secrets
- [ ] Add `AZURE_CREDENTIALS` to GitHub Secrets
- [ ] Deploy infrastructure using `infrastructure/deploy.ps1`
- [ ] Add API keys using `infrastructure/add-api-keys.ps1`
- [ ] Make a test commit and push to trigger pipeline
- [ ] Verify workflow succeeds in Actions tab
- [ ] Check deployment at backend URL
- [ ] Review security scan results

**Questions?** Open an issue or contact the team.
