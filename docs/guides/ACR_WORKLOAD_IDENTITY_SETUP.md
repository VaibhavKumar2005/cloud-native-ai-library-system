# Azure Container Registry Authentication via Workload Identity Federation

This guide shows how to configure GitHub Actions to deploy to Azure Container Apps using Workload Identity Federation (OIDC) instead of stored credentials.

## Why This Matters

**Before (Insecure):**
- Long-lived `AZURE_CREDENTIALS` JSON secret stored in GitHub
- Container registry credentials stored as secrets
- ACR required admin account enabled (security antipattern)
- Risk: If GitHub is compromised, Azure is compromised

**After (Secure):**
- OIDC-based authentication with zero stored credentials
- Workload Identity Federation: GitHub → Azure AD → Azure Resources
- No admin account required on ACR
- Follows zero-trust security principle

## Prerequisites

- Azure CLI installed (`az --version`)
- GitHub repository admin access
- Azure subscription owner or Service Principal creator permissions

## Setup Steps

### Step 1: Create or Identify Your Service Principal

If you don't have one, create it:

```bash
az ad sp create-for-rbac \
  --name verirag-github-actions \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
```

Save the output - you'll need the `appId`.

If you already have one, get the appId:

```bash
SP_APP_ID=$(az ad sp show \
  --id "/subscriptions/YOUR_SUBSCRIPTION_ID/providers/Microsoft.Authorization/roleAssignments" \
  --query "[].principalId" -o tsv | head -1)
echo $SP_APP_ID
```

### Step 2: Create Federated Credential

This allows GitHub Actions to authenticate as your Service Principal without storing credentials:

```bash
az ad app federated-credential create \
  --id YOUR_SP_APP_ID \
  --parameters '{
    "name": "github-verirag",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_GITHUB_ORG/cloud-native-ai-library-system:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Replace:
- `YOUR_SP_APP_ID` with your Service Principal's appId
- `YOUR_GITHUB_ORG` with your GitHub org (e.g., `VaibhavKumar2005`)

### Step 3: Add GitHub Actions Variables (Not Secrets!)

Go to your GitHub repo: **Settings → Environments → production → Variables**

Add these three **variables** (not secrets):

| Variable | Value |
|----------|-------|
| `AZURE_CLIENT_ID` | Your Service Principal app ID |
| `AZURE_TENANT_ID` | Your Azure tenant ID (`az account show --query tenantId -o tsv`) |
| `AZURE_SUBSCRIPTION_ID` | Your subscription ID (`az account show --query id -o tsv`) |
| `REGISTRY_SERVER` | `yourACRname.azurecr.io` |
| `ACR_NAME` | `yourACRname` (without `.azurecr.io`) |
| `AZURE_RESOURCE_GROUP` | Your resource group name |
| `BACKEND_APP_NAME` | Container Apps backend name |
| `CELERY_APP_NAME` | Container Apps worker name |
| `FRONTEND_APP_NAME` | Container Apps frontend name |

### Step 4: Grant Container Apps Permissions to Pull from ACR

Each Container App needs the `acrPull` role on your ACR:

```bash
ACR_ID=$(az acr show \
  --name YOUR_ACR_NAME \
  --query id -o tsv)

# For backend
BACKEND_PRINCIPAL=$(az containerapp show \
  --name YOUR_BACKEND_APP \
  --resource-group YOUR_RG \
  --query identity.principalId -o tsv)

az role assignment create \
  --assignee $BACKEND_PRINCIPAL \
  --role acrPull \
  --scope $ACR_ID

# For Celery worker
WORKER_PRINCIPAL=$(az containerapp show \
  --name YOUR_WORKER_APP \
  --resource-group YOUR_RG \
  --query identity.principalId -o tsv)

az role assignment create \
  --assignee $WORKER_PRINCIPAL \
  --role acrPull \
  --scope $ACR_ID

# For frontend
FRONTEND_PRINCIPAL=$(az containerapp show \
  --name YOUR_FRONTEND_APP \
  --resource-group YOUR_RG \
  --query identity.principalId -o tsv)

az role assignment create \
  --assignee $FRONTEND_PRINCIPAL \
  --role acrPull \
  --scope $ACR_ID
```

### Step 5: Verify Your Registry Server Setting

Make sure your Container Apps are configured to use the correct registry server:

```bash
az containerapp show \
  --name YOUR_BACKEND_APP \
  --resource-group YOUR_RG \
  --query properties.configuration.registries
```

If `registries` is empty, you can optionally configure it:

```bash
az containerapp registry set \
  --name YOUR_BACKEND_APP \
  --resource-group YOUR_RG \
  --server YOUR_ACR_NAME.azurecr.io \
  --identity [system]
```

The `[system]` tells Container Apps to use its system-assigned managed identity (which now has `acrPull`).

## Testing

1. Go to **Actions → VeriRAG Manual ACA Deploy**
2. Click **Run workflow**
3. Select `production` environment and check boxes
4. Watch the logs - you should see:
   ```
   Azure CLI login successful via OIDC
   Successfully logged in to ACR
   ```
5. If it fails at image push, check ACR name in variables

## Troubleshooting

### "Unauthorized to access ACR"
- Verify `acrPull` role is assigned to Container App's managed identity
- Check ACR name matches in variables
- Verify Service Principal has `Contributor` or `ACR Push` role on ACR

### "AZURE_CLIENT_ID not found"
- Make sure variables are in **Variables** tab, not **Secrets**
- Variables don't require `${{ secrets.* }}`

### "Failed to get credential"
- Verify federated credential was created with correct `subject`
- The `subject` must exactly match your GitHub repo and branch

### Cannot push to GHCR
- Keep `REGISTRY_SERVER` as `ghcr.io` for non-ACR registries
- Keep `--username` / `--password` for GHCR login

## Cleanup (Optional)

To remove old insecure credentials:

```bash
# Remove AZURE_CREDENTIALS secret
# In GitHub: Settings → Secrets → Remove AZURE_CREDENTIALS

# Disable admin account on ACR (if it was only for this)
az acr update --name YOUR_ACR_NAME --admin-enabled false
```

## References

- [Azure Workload Identity Federation](https://learn.microsoft.com/en-us/azure/active-directory/workload-identities/workload-identity-federation)
- [GitHub Actions: Workload identity federation](https://github.com/azure/login#workload-identity-federation)
- [Azure Container Registry Authentication](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication)
