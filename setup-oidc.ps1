# VeriRAG Azure OIDC Setup Script for GitHub Actions
# This script establishes the Workload Identity Federation trust between GitHub and Azure
# Run this from your Azure CLI authenticated terminal

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "VeriRAG Azure OIDC Setup Script" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# Configuration values
$CLIENT_ID = "34c83f79-bf46-44fa-87ff-384e99e654de"
$TENANT_ID = "cb90253c-15cb-48c4-b59c-d902b127637d"
$SUBSCRIPTION_ID = "b7d6d48a-9b60-420c-b046-1e1512b81243"

Write-Host "`n[Step 1] Setting up OIDC Federated Credential"  -ForegroundColor Yellow
Write-Host "This links GitHub Actions to your Azure service principal`n"

# Create federated credential JSON
$federatedCredential = @{
    name = "github-verirag-oidc"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:VaibhavKumar2005/cloud-native-ai-library-system:ref:refs/heads/main"
    description = "OIDC trust for GitHub Actions"
    audiences = @("api://AzureADTokenExchange")
}

# Convert to JSON string
$jsonParam = $federatedCredential | ConvertTo-Json -Compress

Write-Host "Creating federated credential with:"
Write-Host "  - Service Principal ID: $CLIENT_ID"
Write-Host "  - Repository: VaibhavKumar2005/cloud-native-ai-library-system"
Write-Host "  - Branch: main"
Write-Host ""

# Run the Azure CLI command
try {
    $result = az ad app federated-credential create `
        --id $CLIENT_ID `
        --parameters $jsonParam
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SUCCESS: Federated credential created!" -ForegroundColor Green
        Write-Host $result
    } else {
        Write-Host "❌ FAILED: Could not create federated credential" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE"
    }
} catch {
    Write-Host "❌ ERROR: $_" -ForegroundColor Red
}

Write-Host "`n[Step 2] Verify Service Principal RBAC Assignment" -ForegroundColor Yellow
Write-Host "Checking if service principal has necessary roles...`n"

# Check existing role assignments
try {
    $roles = az role assignment list `
        --assignee $CLIENT_ID `
        --subscription $SUBSCRIPTION_ID `
        --query "[].roleDefinitionName" -o json
    
    Write-Host "Current roles assigned to service principal:"
    Write-Host $roles
} catch {
    Write-Host "⚠️ Could not list roles: $_" -ForegroundColor Yellow
}

Write-Host "`n[Step 3] GitHub Actions Configuration" -ForegroundColor Yellow
Write-Host "You must add these as VARIABLES (not secrets) in your GitHub repository:`n"

Write-Host "AZURE_CLIENT_ID = $CLIENT_ID" -ForegroundColor Cyan
Write-Host "AZURE_TENANT_ID = $TENANT_ID" -ForegroundColor Cyan
Write-Host "AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID" -ForegroundColor Cyan

Write-Host "`n[Instructions]:" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/settings/variables/actions"
Write-Host "2. Click 'New repository variable'"
Write-Host "3. Add each of the three variables above"
Write-Host "4. IMPORTANT: These are VARIABLES, not SECRETS (they are not sensitive)"
Write-Host ""

Write-Host "`n[Step 4] Delete Old Secrets" -ForegroundColor Yellow
Write-Host "Go to: https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/settings/secrets/actions"
Write-Host "Delete any secrets like: AZURE_CREDENTIALS, AZURE_SECRET, etc.`n"

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Setup Complete! Your workflow now uses OIDC (Zero Stored Credentials)" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
