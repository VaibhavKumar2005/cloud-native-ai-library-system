#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick Vault secrets injection for VeriRAG dual-agent system

.DESCRIPTION
    Adds GOOGLE_API_KEY (Generator Agent) and GROQ_API_KEY (Critic Agent) to Vault
#>

Write-Host "`n🔐 VeriRAG Vault Setup - Dual-Agent Configuration" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# Check if Vault container is running
$vaultRunning = docker ps --filter "name=rag-vault" --format "{{.Names}}"
if (-not $vaultRunning) {
    Write-Host "❌ Vault container not running!" -ForegroundColor Red
    Write-Host "   Fix: docker-compose up -d rag-vault" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Vault container is running`n" -ForegroundColor Green

# Prompt for API keys
Write-Host "Enter your API keys for the dual-agent system:" -ForegroundColor Yellow
Write-Host "(Press Ctrl+C to cancel)`n" -ForegroundColor Gray

$googleKey = Read-Host "GOOGLE_API_KEY (Generator Agent - Gemini)"
$groqKey = Read-Host "GROQ_API_KEY (Critic Agent - Llama-3)"

if (-not $googleKey -or -not $groqKey) {
    Write-Host "`n❌ Both API keys are required!" -ForegroundColor Red
    exit 1
}

Write-Host "`n💉 Injecting secrets into Vault..." -ForegroundColor Yellow

# Create JSON payload (no extra 'data' wrapper for KV v2)
$payload = @{
    GOOGLE_API_KEY = $googleKey
    GROQ_API_KEY = $groqKey
    DB_NAME = "verirag_db"
    DB_USER = "admin"
    DB_PASSWORD = "devpassword"
    DB_HOST = "rag-db"
    DB_PORT = "5432"
} | ConvertTo-Json -Depth 5

# Write to Vault
$payload | docker exec -i rag-vault sh -c 'cat > /tmp/payload.json'
$result = docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault kv put secret/myapp "@/tmp/payload.json" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SUCCESS! API keys stored in Vault" -ForegroundColor Green
    Write-Host "`nVerifying..." -ForegroundColor Yellow
    
    $verify = docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault kv get -mount=secret myapp 2>&1
    if ($verify -match "GOOGLE_API_KEY" -and $verify -match "GROQ_API_KEY") {
        Write-Host "✅ Verification passed!" -ForegroundColor Green
        Write-Host "`n🎯 Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Run: .\test-pdf-pipeline.ps1" -ForegroundColor White
        Write-Host "  2. Or test manually: docker logs -f rag-celery-worker" -ForegroundColor White
    }
} else {
    Write-Host "❌ Failed to inject secrets: $result" -ForegroundColor Red
    exit 1
}
