<#
.SYNOPSIS
    Complete Azure setup for VeriRAG CI/CD deployment
    
.DESCRIPTION
    Sets up:
    - Container Apps (backend, frontend, celery worker)
    - Managed Identity with RBAC roles
    - ACR access for container apps
    - GitHub repository variables and secrets
    
.PARAMETER ResourceGroup
    Azure Resource Group name (default: verirag-rg)
    
.PARAMETER Location
    Azure region (default: eastus)
    
.PARAMETER SubscriptionId
    Azure Subscription ID
    
.EXAMPLE
    .\azure-deployment-setup.ps1 -SubscriptionId "your-sub-id"
#>

param(
    [string]$ResourceGroup = "verirag-rg",
    [string]$Location = "eastus",
    [string]$SubscriptionId,
    [string]$GitHubRepo = "VaibhavKumar2005/cloud-native-ai-library-system"
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{
        Info    = "Cyan"
        Success = "Green"
        Warning = "Yellow"
        Error   = "Red"
    }
    Write-Host "[$Type] $Message" -ForegroundColor $colors[$Type]
}

function Confirm-Prerequisites {
    Write-Status "Checking prerequisites..." "Info"
    
    # Check Azure CLI
    try {
        az version | Out-Null
        Write-Status "✅ Azure CLI installed" "Success"
    } catch {
        throw "❌ Azure CLI not found. Install from https://aka.ms/azure-cli"
    }
    
    # Check GitHub CLI
    try {
        gh version | Out-Null
        Write-Status "✅ GitHub CLI installed" "Success"
    } catch {
        throw "❌ GitHub CLI not found. Install from https://cli.github.com"
    }
    
    # Check Python (for app setup)
    try {
        python --version | Out-Null
        Write-Status "✅ Python installed" "Success"
    } catch {
        Write-Status "⚠️  Python not found in PATH (optional)" "Warning"
    }
}

function Set-AzureSubscription {
    param([string]$SubId)
    
    if ([string]::IsNullOrEmpty($SubId)) {
        Write-Status "Getting default subscription..." "Info"
        $SubId = (az account show --query id -o tsv)
    }
    
    Write-Status "Setting subscription to: $SubId" "Info"
    az account set --subscription $SubId
    Write-Status "✅ Subscription set" "Success"
    
    return $SubId
}

function New-ContainerAppEnvironment {
    param(
        [string]$ResourceGroup,
        [string]$Location,
        [string]$EnvironmentName = "verirag-env"
    )
    
    Write-Status "Checking Container App Environment..." "Info"
    
    # Check if specific environment exists in resource group
    $exists = az containerapp env list --resource-group $ResourceGroup --query "[?name=='$EnvironmentName'].id" -o tsv 2>$null
    
    if ($exists) {
        Write-Status "✅ Environment already exists: $EnvironmentName" "Success"
        return $exists
    }
    
    # Check if ANY environment exists in subscription (limit is 1 per subscription in some regions)
    $allEnvs = az containerapp env list --query "[].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
    
    if ($allEnvs -and $allEnvs.Count -gt 0) {
        $existingEnv = $allEnvs[0].name
        Write-Status "⚠️  Found existing environment in subscription: $existingEnv" "Warning"
        Write-Status "Using existing environment instead of creating new one" "Info"
        
        # Return the existing environment
        $envId = az containerapp env list --query "[0].id" -o tsv
        Write-Status "✅ Using environment: $existingEnv" "Success"
        return $envId
    }
    
    # Create new environment only if none exists
    Write-Status "Creating new Container App Environment..." "Info"
    az containerapp env create `
        --name $EnvironmentName `
        --resource-group $ResourceGroup `
        --location $Location | Out-Null
    
    Write-Status "✅ Created environment: $EnvironmentName" "Success"
}

function New-ContainerApp {
    param(
        [string]$AppName,
        [string]$ResourceGroup,
        [string]$EnvironmentName,
        [string]$Image,
        [int]$TargetPort = 8000,
        [bool]$RequiresIngress = $true
    )
    
    Write-Status "Setting up container app: $AppName" "Info"
    
    $exists = az containerapp show --name $AppName --resource-group $ResourceGroup --query "id" -o tsv 2>$null
    
    if ($exists) {
        Write-Status "✅ Container app already exists: $AppName" "Success"
        return $exists
    }
    
    $params = @(
        "--name", $AppName
        "--resource-group", $ResourceGroup
        "--environment", $EnvironmentName
        "--image", $Image
    )
    
    if ($RequiresIngress) {
        $params += @("--ingress", "external", "--target-port", $TargetPort)
    }
    
    Write-Status "Creating container app: $AppName..." "Info"
    $result = az containerapp create @params 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        # If environment name failed, try to get environment ID and retry
        Write-Status "ℹ️  Attempting to find environment by ID..." "Info"
        $envId = az containerapp env list --query "[0].id" -o tsv 2>$null
        if ($envId) {
            $params[5] = $envId  # Replace environment name with ID
            $result = az containerapp create @params 2>&1
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "❌ Failed to create $AppName" "Error"
        Write-Status "Error: $result" "Error"
        throw "Cannot create container app: $_"
    }
    
    Write-Status "✅ Created container app: $AppName" "Success"
    return $AppName
}

function Grant-ACRAccess {
    param(
        [string]$AppName,
        [string]$ResourceGroup,
        [string]$ACRName,
        [string]$SubscriptionId
    )
    
    Write-Status "Granting ACR access to $AppName..." "Info"
    
    # Get managed identity
    $identity = az containerapp identity show `
        --name $AppName `
        --resource-group $ResourceGroup `
        --query principalId -o tsv
    
    if ([string]::IsNullOrEmpty($identity)) {
        Write-Status "⚠️  No system identity found, skipping ACR role assignment" "Warning"
        return
    }
    
    # Get ACR resource ID
    $acrResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.ContainerRegistry/registries/$ACRName"
    
    # Check if role already assigned
    $existing = az role assignment list `
        --assignee $identity `
        --role "AcrPull" `
        --scope $acrResourceId `
        --query "[0].id" -o tsv
    
    if ($existing) {
        Write-Status "✅ AcrPull role already assigned to $AppName" "Success"
        return
    }
    
    # Assign role
    az role assignment create `
        --assignee $identity `
        --role "AcrPull" `
        --scope $acrResourceId | Out-Null
    
    Write-Status "✅ Granted AcrPull role to $AppName" "Success"
}

function Set-GitHubVariables {
    param(
        [string]$Repo,
        [hashtable]$Variables
    )
    
    Write-Status "Setting GitHub variables..." "Info"
    
    foreach ($key in $Variables.Keys) {
        $value = $Variables[$key]
        Write-Status "  Setting $key..." "Info"
        
        gh variable set $key --body "$value" --repo $Repo
        Write-Status "  ✅ $key set" "Success"
    }
}

function Set-GitHubSecrets {
    param(
        [string]$Repo,
        [hashtable]$Secrets
    )
    
    Write-Status "Setting GitHub secrets..." "Info"
    
    foreach ($key in $Secrets.Keys) {
        $value = $Secrets[$key]
        Write-Status "  Setting $key..." "Info"
        
        $value | gh secret set $key --repo $Repo
        Write-Status "  ✅ $key set" "Success"
    }
}

function Get-ACRCredentials {
    param([string]$ACRName)
    
    Write-Status "Retrieving ACR credentials..." "Info"
    
    $credentials = az acr credential show --name $ACRName
    return $credentials | ConvertFrom-Json
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

try {
    Write-Status "🚀 Starting VeriRAG deployment setup..." "Info"
    
    # Verify prerequisites
    Confirm-Prerequisites
    
    # Set subscription
    $SubscriptionId = Set-AzureSubscription -SubId $SubscriptionId
    if ([string]::IsNullOrEmpty($SubscriptionId)) {
        throw "Failed to set subscription"
    }
    
    # Verify resource group exists
    Write-Status "Checking resource group: $ResourceGroup..." "Info"
    $rg = az group show --name $ResourceGroup --query "id" -o tsv 2>$null
    if (!$rg) {
        throw "Resource group '$ResourceGroup' not found. Create it first with: az group create --name $ResourceGroup --location $Location"
    }
    Write-Status "✅ Resource group exists" "Success"
    
    # Create container app environment
    $envName = "verirag-env"
    $envId = New-ContainerAppEnvironment -ResourceGroup $ResourceGroup -Location $Location -EnvironmentName $envName
    
    # Container app configuration
    $acrRegistry = "acrvaibhavrag2026"
    $acrUrl = "$acrRegistry.azurecr.io"
    $defaultImage = "$acrUrl/verirag/backend:latest"
    
    # Create container apps (use environment ID instead of name)
    Write-Status "Creating container apps..." "Info"
    
    New-ContainerApp `
        -AppName "ca-verirag-dev-backend" `
        -ResourceGroup $ResourceGroup `
        -EnvironmentName $envId `
        -Image $defaultImage `
        -TargetPort 8000 `
        -RequiresIngress $true
    
    New-ContainerApp `
        -AppName "ca-verirag-dev-frontend" `
        -ResourceGroup $ResourceGroup `
        -EnvironmentName $envId `
        -Image "$acrUrl/verirag/frontend:latest" `
        -TargetPort 5173 `
        -RequiresIngress $true
    
    New-ContainerApp `
        -AppName "ca-verirag-dev-worker" `
        -ResourceGroup $ResourceGroup `
        -EnvironmentName $envId `
        -Image $defaultImage `
        -RequiresIngress $false
    
    # Grant ACR access
    Write-Status "Configuring ACR access..." "Info"
    Grant-ACRAccess -AppName "ca-verirag-dev-backend" -ResourceGroup $ResourceGroup -ACRName $acrRegistry -SubscriptionId $SubscriptionId
    Grant-ACRAccess -AppName "ca-verirag-dev-frontend" -ResourceGroup $ResourceGroup -ACRName $acrRegistry -SubscriptionId $SubscriptionId
    Grant-ACRAccess -AppName "ca-verirag-dev-worker" -ResourceGroup $ResourceGroup -ACRName $acrRegistry -SubscriptionId $SubscriptionId
    
    # Get backend FQDN for VITE_API_URL
    Write-Status "Retrieving backend FQDN..." "Info"
    $backendFQDN = az containerapp show `
        --name "ca-verirag-dev-backend" `
        --resource-group $ResourceGroup `
        --query "properties.configuration.ingress.fqdn" -o tsv
    
    if ([string]::IsNullOrEmpty($backendFQDN)) {
        $backendFQDN = "https://ca-verirag-dev-backend.$Location.azurecontainer.io"
        Write-Status "⚠️  Could not retrieve FQDN, using pattern: $backendFQDN" "Warning"
    } else {
        $backendFQDN = "https://$backendFQDN"
    }
    
    # Get Azure AD app info for OIDC
    Write-Status "Checking OIDC configuration..." "Info"
    
    $oidcIdentity = az identity show --name "github-oidc-verirag" --resource-group $ResourceGroup --query appId -o tsv 2>$null
    if (!$oidcIdentity) {
        Write-Status "⚠️  OIDC identity not found. Please set up GitHub OIDC in Azure AD manually" "Warning"
        Write-Status "    Run: https://aka.ms/github-oidc-setup" "Info"
        $clientId = Read-Host "Enter your Azure AD app client ID (for GitHub secrets)"
        $tenantId = Read-Host "Enter your Azure AD tenant ID"
    } else {
        $clientId = $oidcIdentity
        $tenantId = az account show --query tenantId -o tsv
    }
    
    # Set GitHub variables
    if ($GitHubRepo) {
        Write-Status "Configuring GitHub repository..." "Info"
        
        $variables = @{
            AZURE_RESOURCE_GROUP = $ResourceGroup
            BACKEND_APP_NAME     = "ca-verirag-dev-backend"
            CELERY_APP_NAME      = "ca-verirag-dev-worker"
            FRONTEND_APP_NAME    = "ca-verirag-dev-frontend"
            VITE_API_URL         = $backendFQDN
        }
        
        Set-GitHubVariables -Repo $GitHubRepo -Variables $variables
        
        # Set GitHub secrets
        $secrets = @{
            AZURE_CLIENT_ID       = $clientId
            AZURE_TENANT_ID       = $tenantId
            AZURE_SUBSCRIPTION_ID = $SubscriptionId
        }
        
        Set-GitHubSecrets -Repo $GitHubRepo -Secrets $secrets
    }
    
    # Summary
    Write-Status "========================================" "Success"
    Write-Status "✅ Setup Complete!" "Success"
    Write-Status "========================================" "Success"
    
    Write-Output @"
📋 Configuration Summary:

Azure Resources:
  ├─ Resource Group: $ResourceGroup
  ├─ Location: $Location
  ├─ Container Apps Environment: $envName
  ├─ Backend App: ca-verirag-dev-backend (port 8000)
  ├─ Frontend App: ca-verirag-dev-frontend (port 5173)
  └─ Worker App: ca-verirag-dev-worker

GitHub Configuration:
  ├─ Repository: $GitHubRepo
  ├─ Variables: AZURE_RESOURCE_GROUP, BACKEND_APP_NAME, CELERY_APP_NAME, FRONTEND_APP_NAME, VITE_API_URL
  └─ Secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID

Next Steps:
  1. Verify all health checks pass:
     - az containerapp show -n ca-verirag-dev-backend -g $ResourceGroup --query properties.configuration.ingress.fqdn
     
  2. Push to main branch to trigger CI/CD:
     - git push origin main
     
  3. Monitor the pipeline:
     - https://github.com/$GitHubRepo/actions

"@
    
} catch {
    Write-Status "❌ Error: $_" "Error"
    exit 1
}
