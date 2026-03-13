# Configure GitHub Secrets and Variables for Manual ACA Deployment

This guide walks you through setting up the required GitHub secrets and variables for the manual ACA deployment workflow.

## 📋 Prerequisites

Before starting, you need:
- ✅ An Azure subscription with Container Apps deployed
- ✅ Azure Service Principal with Container Apps permissions (Owner or Contributor role on resource group)
- ✅ A container registry account:
  - **GitHub Container Registry (GHCR)** — Recommended for cost control (free)
  - **Docker Hub** — Also free
  - **Azure Container Registry (ACR)** — Can upgrade later

## 🔑 Step 1: Create Container Registry Credentials

### Option A: GitHub Container Registry (GHCR) — Recommended

GHCR is free and integrates seamlessly with GitHub Actions.

1. **Create a Personal Access Token (PAT)**:
   - Go to: https://github.com/settings/tokens
   - Click **Generate new token (classic)**
   - Scope: Select `write:packages` and `read:packages`
   - Copy the token (you'll need it in a moment)

2. **Username**: Your GitHub username (lowercase)

3. **Password**: The PAT token you just created

### Option B: Docker Hub

1. **Create a Personal Access Token**:
   - Go to: https://hub.docker.com/settings/security
   - Click **New Access Token**
   - Scope: Select **Read, Write & Delete**
   - Copy the token

2. **Username**: Your Docker Hub username

3. **Password**: The token you just created

### Option C: Azure Container Registry (ACR)

1. **Get ACR credentials**:
   ```powershell
   az acr show --name <your-acr-name> --resource-group <rg-name> --query loginServer --output tsv
   az acr credential show --name <your-acr-name>
   ```

2. **Username**: From `az acr credential show` (usually `<acr-name>`)

3. **Password**: From `az acr credential show`

---

## 🔐 Step 2: Add GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions → Secrets tab**

### Required Secrets

#### 1. `REGISTRY_USERNAME`
- **Value**: Your Docker Hub username, GitHub username (for GHCR), or ACR username
- Click **New repository secret**
- Name: `REGISTRY_USERNAME`
- Value: (paste your username)

#### 2. `REGISTRY_PASSWORD`
- **Value**: Your Docker Hub token, GitHub PAT (for GHCR), or ACR password
- Click **New repository secret**
- Name: `REGISTRY_PASSWORD`
- Value: (paste your token/password)

#### 3. `AZURE_CREDENTIALS`
- **Value**: Azure Service Principal JSON

To create the Service Principal:

```powershell
# List available subscriptions
az account list --output table

# Set your subscription ID
$SUBSCRIPTION_ID = "<your-subscription-id>"
az account set --subscription $SUBSCRIPTION_ID

# Create Service Principal for Container Apps
az ad sp create-for-rbac --name "github-actions-verirag" `
  --role Contributor `
  --scopes /subscriptions/$SUBSCRIPTION_ID `
  --output json
```

Copy the entire JSON output (including `clientId`, `clientSecret`, `subscriptionId`, `tenantId`).

In GitHub:
- Click **New repository secret**
- Name: `AZURE_CREDENTIALS`
- Value: (paste the entire JSON)

---

## 📝 Step 3: Add GitHub Variables

Go to your repository: **Settings → Secrets and variables → Actions → Variables tab**

### Required Variables

#### 1. `AZURE_RESOURCE_GROUP`
- **Value**: The name of your Azure resource group
- Example: `rg-verirag-dev`

#### 2. `BACKEND_APP_NAME`
- **Value**: The name of your backend Container App
- Example: `ca-verirag-backend`

#### 3. `CELERY_APP_NAME`
- **Value**: The name of your Celery worker Container App
- Example: `ca-verirag-celery-worker`

#### 4. `FRONTEND_APP_NAME`
- **Value**: The name of your frontend Container App
- Example: `ca-verirag-frontend`

### Optional Variables

#### 5. `REGISTRY_SERVER` (optional)
- **Default**: `ghcr.io` (GitHub Container Registry)
- **Other options**:
  - `docker.io` (Docker Hub)
  - Your ACR server: `yourregistry.azurecr.io`

#### 6. `IMAGE_NAMESPACE` (optional)
- **Default**: Your GitHub username (for GHCR)
- For Docker Hub: Your Docker Hub namespace
- Example: `vaibhavkumar2005`

#### 7. `VITE_API_URL` (optional)
- **Value**: Your backend API URL
- Example: `https://ca-verirag-backend.region.azurecontainerapps.io`

---

## ✅ Verification Checklist

Before triggering the deployment:

- [ ] `REGISTRY_USERNAME` secret added
- [ ] `REGISTRY_PASSWORD` secret added
- [ ] `AZURE_CREDENTIALS` secret added
- [ ] `AZURE_RESOURCE_GROUP` variable set
- [ ] `BACKEND_APP_NAME` variable set
- [ ] `CELERY_APP_NAME` variable set
- [ ] `FRONTEND_APP_NAME` variable set
- [ ] (Optional) `REGISTRY_SERVER` variable set
- [ ] (Optional) `IMAGE_NAMESPACE` variable set
- [ ] (Optional) `VITE_API_URL` variable set

---

## 🚀 Trigger Manual Deployment

Once all secrets/variables are configured:

1. Go to your repository
2. Click **Actions** tab
3. Select **VeriRAG Manual ACA Deploy** workflow
4. Click **Run workflow**
5. Fill in the inputs:
   - **git_ref**: `main` (or your branch)
   - **environment**: `production`
   - **deploy_backend**: `true`
   - **deploy_worker**: `true`
   - **deploy_frontend**: `true`
6. Click **Run workflow**

The deployment will:
- Build Docker images
- Push to your configured registry
- Update Azure Container Apps
- Run health checks
- Report results in the Actions summary

---

## 🔧 Troubleshooting

### "Access Denied" on Docker Push
- Check that `REGISTRY_USERNAME` and `REGISTRY_PASSWORD` are correct
- For GHCR: Verify the PAT has `write:packages` scope
- For Docker Hub: Verify the token has Read, Write & Delete scope

### "Invalid Azure Credentials"
- Ensure `AZURE_CREDENTIALS` is the complete JSON (not truncated)
- Verify the Service Principal has Contributor role on the resource group

### Health Check Fails After Deploy
- Container Apps may need 30-60 seconds to warm up
- Check container app logs: `az containerapp logs show --name <app-name> --resource-group <rg-name>`

---

## ✨ Next Steps

Once deployment is successful:
1. Access your backend at the Container App URL
2. Run smoke tests: `/api/health/`
3. Upload a test PDF document
4. Query the document to verify the full pipeline

Enjoy your Azure-native showcase! 🎉
