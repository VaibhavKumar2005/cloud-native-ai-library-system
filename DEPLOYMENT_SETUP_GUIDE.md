# VeriRAG Deployment Setup Guide

Your subscription already has 1 Container App Environment (limit reached). Here's the manual setup:

## Step 1: Get Existing Environment Details

```powershell
# Find the existing environment
$env = az containerapp env list --query "[0]" -o json | ConvertFrom-Json
Write-Host "Environment: $($env.name)"
Write-Host "Resource Group: $($env.resourceGroup)"
Write-Host "ID: $($env.id)"

# Use this environment for all container apps
$ENV_ID = $env.id
$ENV_NAME = $env.name
$RG = $env.resourceGroup
```

## Step 2: Configure ACR Authentication

```powershell
# Enable ACR admin account (simpler for CI/CD)
$acrName = "acrvaibhavrag2026"
az acr update -n $acrName --admin-enabled true

# Get admin credentials
$acrCreds = az acr credential show -n $acrName | ConvertFrom-Json
$acrUser = $acrCreds.username
$acrPass = $acrCreds.passwords[0].value

Write-Host "ACR Username: $acrUser"
Write-Host "ACR Password: $($acrPass.Substring(0,10))..."
```

## Step 3: Create Container Apps with ACR Credentials

```powershell
# Backend App
az containerapp create `
  --name ca-verirag-dev-backend `
  --resource-group $RG `
  --environment $ENV_ID `
  --image acrvaibhavrag2026.azurecr.io/verirag/backend:latest `
  --ingress external `
  --target-port 8000 `
  --registry-server acrvaibhavrag2026.azurecr.io `
  --registry-username $acrUser `
  --registry-password $acrPass

# Frontend App
az containerapp create `
  --name ca-verirag-dev-frontend `
  --resource-group $RG `
  --environment $ENV_ID `
  --image acrvaibhavrag2026.azurecr.io/verirag/frontend:latest `
  --ingress external `
  --target-port 5173 `
  --registry-server acrvaibhavrag2026.azurecr.io `
  --registry-username $acrUser `
  --registry-password $acrPass

# Worker App (no ingress)
az containerapp create `
  --name ca-verirag-dev-worker `
  --resource-group $RG `
  --environment $ENV_ID `
  --image acrvaibhavrag2026.azurecr.io/verirag/backend:latest `
  --registry-server acrvaibhavrag2026.azurecr.io `
  --registry-username $acrUser `
  --registry-password $acrPass
```

## Step 4: Get Container App FQDNs

```powershell
# Backend FQDN
$backendFQDN = az containerapp show `
  -n ca-verirag-dev-backend `
  -g $RG `
  --query "properties.configuration.ingress.fqdn" -o tsv

# Frontend FQDN  
$frontendFQDN = az containerapp show `
  -n ca-verirag-dev-frontend `
  -g $RG `
  --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host "Backend: https://$backendFQDN"
Write-Host "Frontend: https://$frontendFQDN"
```

## Step 5: Set GitHub Variables

```powershell
$repo = "VaibhavKumar2005/cloud-native-ai-library-system"

gh variable set AZURE_RESOURCE_GROUP --body $RG --repo $repo
gh variable set BACKEND_APP_NAME --body "ca-verirag-dev-backend" --repo $repo
gh variable set CELERY_APP_NAME --body "ca-verirag-dev-worker" --repo $repo
gh variable set FRONTEND_APP_NAME --body "ca-verirag-dev-frontend" --repo $repo
gh variable set VITE_API_URL --body "https://$backendFQDN" --repo $repo
```

## Step 6: Set GitHub Secrets (with OIDC or PAT)

### Option A: Using OIDC (Recommended - Passwordless)

```powershell
# Get your Azure Tenant ID
$tenantId = az account show --query tenantId -o tsv

# Get your Azure Subscription ID
$subId = az account show --query id -o tsv

# Create an Entra ID app for GitHub OIDC (run once)
$appName = "github-oidc-verirag"
$appId = az ad app create --display-name $appName --query appId -o tsv

# Create federated credentials for GitHub
az ad app federated-credential create `
  --id $appId `
  --parameters '{
    "name": "github-repo",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:VaibhavKumar2005/cloud-native-ai-library-system:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Set GitHub secrets
$repo = "VaibhavKumar2005/cloud-native-ai-library-system"
echo $appId | gh secret set AZURE_CLIENT_ID --repo $repo
echo $tenantId | gh secret set AZURE_TENANT_ID --repo $repo
echo $subId | gh secret set AZURE_SUBSCRIPTION_ID --repo $repo

Write-Host "✅ OIDC configured!"
```

### Option B: Using Personal Access Token (Simpler for now)

```powershell
# Create a PAT at: https://github.com/settings/tokens/new
# Scopes needed: repo, admin:repo_hook, workflow
# Store it as: AZURE_CREDENTIALS

# For now, just use dummy values to get pipeline working
$repo = "VaibhavKumar2005/cloud-native-ai-library-system"

# Get real values
$clientId = az ad app list --display-name github-oidc-verirag --query "[0].appId" -o tsv
if ($clientId) {
  echo $clientId | gh secret set AZURE_CLIENT_ID --repo $repo
}

$tenantId = az account show --query tenantId -o tsv
echo $tenantId | gh secret set AZURE_TENANT_ID --repo $repo

$subId = az account show --query id -o tsv
echo $subId | gh secret set AZURE_SUBSCRIPTION_ID --repo $repo

Write-Host "✅ GitHub secrets configured!"
```

## Step 7: Verify Setup

```powershell
# Check container apps exist
az containerapp show -n ca-verirag-dev-backend -g $RG --query "name,id"
az containerapp show -n ca-verirag-dev-frontend -g $RG --query "name,id"
az containerapp show -n ca-verirag-dev-worker -g $RG --query "name,id"

# Check GitHub variables
gh variable list --repo VaibhavKumar2005/cloud-native-ai-library-system

# Check GitHub secrets
gh secret list --repo VaibhavKumar2005/cloud-native-ai-library-system
```

## Step 8: Push to Trigger Pipeline

```powershell
cd "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"
git add .
git commit -m "chore: deployment infrastructure setup" --allow-empty
git push origin main
```

Then visit: https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/actions

---

## Troubleshooting

### Container Apps Already Exist?
```powershell
# Check what exists
az containerapp list -g verirag-rg

# Delete if needed
az containerapp delete -n ca-verirag-dev-backend -g verirag-rg --yes
```

### ACR Image Pull Still Failing?
```powershell
# Check container app status
az containerapp show -n ca-verirag-dev-backend -g verirag-rg --query "properties.provisionState"

# View logs
az containerapp logs show -n ca-verirag-dev-backend -g verirag-rg --tail 50
```

### GitHub Secrets Not Working?
```powershell
# Verify they're set
gh secret list --repo VaibhavKumar2005/cloud-native-ai-library-system

# They should show: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
```
