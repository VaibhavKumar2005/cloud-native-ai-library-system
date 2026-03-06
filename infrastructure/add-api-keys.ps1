# Add API Keys to Azure Key Vault (Post-Deployment)

Write-Host "🔐 Adding API Keys to Azure Key Vault" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Get Key Vault name from Terraform output
$kvName = terraform output -raw key_vault_name 2>$null

if (!$kvName) {
    Write-Host "❌ Could not get Key Vault name from Terraform." -ForegroundColor Red
    Write-Host "   Make sure you've run deploy.ps1 first." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found Key Vault: $kvName`n" -ForegroundColor Green

# Get API keys from user
Write-Host "📝 Enter your API keys:`n" -ForegroundColor Yellow

$googleApiKey = Read-Host "GOOGLE_API_KEY (from ai.google.dev)"
$groqApiKey = Read-Host "GROQ_API_KEY (from console.groq.com)"

if (!$googleApiKey -or !$groqApiKey) {
    Write-Host "`n❌ Both API keys are required" -ForegroundColor Red
    exit 1
}

# Add secrets to Key Vault
Write-Host "`n🔑 Adding secrets to Key Vault..." -ForegroundColor Yellow

az keyvault secret set --vault-name $kvName --name "GOOGLE-API-KEY" --value $googleApiKey | Out-Null
Write-Host "  ✅ GOOGLE_API_KEY added" -ForegroundColor Green

az keyvault secret set --vault-name $kvName --name "GROQ-API-KEY" --value $groqApiKey | Out-Null
Write-Host "  ✅ GROQ_API_KEY added" -ForegroundColor Green

Write-Host "`n✅ All secrets configured!" -ForegroundColor Green
Write-Host "`n🎯 Your API can now access LLM providers via Azure Key Vault" -ForegroundColor Cyan
Write-Host "   The Container Apps will fetch these at runtime.`n" -ForegroundColor Gray
