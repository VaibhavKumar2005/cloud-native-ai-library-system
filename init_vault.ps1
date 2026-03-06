# init_vault.ps1 - Automates Vault Setup for Windows (Fixed for rag-vault)

$CONTAINER_NAME = "rag-vault"

Write-Host "🚀 Starting Vault Setup..." -ForegroundColor Cyan

# 1. Ensure Vault container is running
Write-Host "Checking Vault container..."
docker-compose up -d rag-vault
Start-Sleep -Seconds 5

# 2. Check Vault Status
try {
    $status = docker exec $CONTAINER_NAME vault status -format=json | ConvertFrom-Json
} catch {
    Write-Host "⚠️ Vault container ($CONTAINER_NAME) is not responding. Ensure Docker is running." -ForegroundColor Red
    exit 1
}

if (-not $status.initialized) {
    Write-Host "⚠️ Vault is not initialized. Initializing now..." -ForegroundColor Yellow
    $init_output = docker exec $CONTAINER_NAME vault operator init -key-shares=1 -key-threshold=1 -format=json
    $init_json = $init_output | ConvertFrom-Json
    
    # Save keys to a file for the user
    $root_token = $init_json.root_token
    $unseal_key = $init_json.unseal_keys_b64[0]
    
    "Root Token: $root_token" | Out-File "vault_keys.txt"
    "Unseal Key: $unseal_key" | Out-File "vault_keys.txt" -Append
    
    Write-Host "✅ Vault Initialized. Keys saved to 'vault_keys.txt'. KEEP THIS SAFE!" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Vault is already initialized." -ForegroundColor Gray
    
    # Try to read keys from file if they exist
    if (Test-Path "vault_keys.txt") {
        $lines = Get-Content "vault_keys.txt"
        $unseal_key = ($lines | Select-String "Unseal Key:").ToString().Split(": ")[1].Trim()
        $root_token = ($lines | Select-String "Root Token:").ToString().Split(": ")[1].Trim()
    } else {
        $unseal_key = Read-Host "Enter your Vault Unseal Key"
        $root_token = Read-Host "Enter your Root Token"
    }
}

# 3. Unseal Vault
Write-Host "🔓 Unsealing Vault..."
docker exec $CONTAINER_NAME vault operator unseal $unseal_key

# 4. Login
Write-Host "🔑 Logging in..."
docker exec $CONTAINER_NAME vault login $root_token

# 5. Enable KV Secrets Engine (Version 2)
Write-Host "⚙️ Enabling KV secrets engine..."
# We suppress errors here in case it's already enabled
docker exec $CONTAINER_NAME vault secrets enable -path=secret kv-v2 2>$null

# 6. Inject Secrets
$google_api_key = Read-Host "Please enter your GOOGLE_API_KEY (starts with AIza...)"
$groq_api_key = Read-Host "Please enter your GROQ_API_KEY (from console.groq.com)"

Write-Host "💉 Injecting secrets into 'secret/data/myapp'..."

# Create the JSON payload for the secrets
$secrets = @{
    data = @{
        GOOGLE_API_KEY = $google_api_key
        GROQ_API_KEY   = $groq_api_key
        DB_NAME        = "verirag_db"
        DB_USER        = "admin"
        DB_PASSWORD    = "devpassword"
        DB_HOST        = "rag-db"
        DB_PORT        = "5432"
    }
}
# Convert to JSON
$json_payload = $secrets | ConvertTo-Json -Depth 5

# Write to a temp file inside the container
$json_payload | docker exec -i $CONTAINER_NAME sh -c 'cat > /tmp/payload.json'

# Inject into Vault
docker exec $CONTAINER_NAME vault kv put secret/myapp "@/tmp/payload.json"

Write-Host "✅ SUCCESS! Secrets are in Vault." -ForegroundColor Green
Write-Host "👉 You can now run: docker-compose up --build" -ForegroundColor Cyan