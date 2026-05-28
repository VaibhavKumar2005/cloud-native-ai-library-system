# VeriRAG Azure Container Apps Deployment Script
# For GitHub Student Pack - uses provided subscription ID

$SubscriptionId = "b7d6d48a-9b60-420c-b046-1e1512b81243"

Write-Host "[*] VeriRAG Azure Deployment (Scale-to-Zero)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check Azure CLI
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Azure CLI not found. Install from: https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}

# Check Terraform
if (!(Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Terraform not found. Install from: https://terraform.io/downloads" -ForegroundColor Red
    exit 1
}

Write-Host "[+] Prerequisites check passed" -ForegroundColor Green

# Azure Login
Write-Host "[*] Logging into Azure..." -ForegroundColor Yellow
az login

# Set subscription
Write-Host "[*] Setting subscription to: $SubscriptionId" -ForegroundColor Yellow
az account set --subscription $SubscriptionId

# Show current subscription
$sub = az account show --query "{Name:name, ID:id}" -o json | ConvertFrom-Json
Write-Host "[+] Using subscription: $($sub.Name) ($($sub.ID))" -ForegroundColor Green

# Generate secrets if terraform.tfvars doesn't exist
if (!(Test-Path "terraform.tfvars")) {
    Write-Host "[*] Creating terraform.tfvars with generated secrets..." -ForegroundColor Yellow
    
    # Generate PostgreSQL password
    $pgPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_}) + "!@#"
    
    # Generate Django secret key
    $djangoSecret = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(50))
    
    $tfvars = @"
# VeriRAG Terraform Variables (Auto-generated)
location     = "centralindia"
project_name = "verirag"
environment  = "dev"
acr_name     = "acrvaibhavrag2026"

# PostgreSQL Credentials
pg_admin_user     = "veriragadmin"
pg_admin_password = "$pgPassword"

# Django Secret Key
django_secret_key = "$djangoSecret"
"@
    
    $tfvars | Out-File -FilePath "terraform.tfvars" -Encoding UTF8
    Write-Host "[+] terraform.tfvars created with secure passwords" -ForegroundColor Green
} else {
    Write-Host "[+] Using existing terraform.tfvars" -ForegroundColor Green
}

# Initialize Terraform
Write-Host "[*] Initializing Terraform..." -ForegroundColor Yellow
terraform init

if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Terraform init failed" -ForegroundColor Red
    exit 1
}

# Plan
Write-Host "[*] Creating deployment plan..." -ForegroundColor Yellow
terraform plan -out=tfplan

if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Terraform plan failed" -ForegroundColor Red
    exit 1
}

# Confirm deployment
Write-Host "[!] This will deploy to Azure and start consuming credits." -ForegroundColor Yellow
Write-Host "    Estimated cost when idle: ~$1.50/day (PostgreSQL + Redis)" -ForegroundColor Yellow
Write-Host "    Compute cost when idle: $0.00 (scale-to-zero)" -ForegroundColor Green
Write-Host ""

$confirm = Read-Host "Deploy now? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Apply
Write-Host "[*] Deploying infrastructure..." -ForegroundColor Cyan
terraform apply tfplan

if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Deployment failed" -ForegroundColor Red
    exit 1
}

# Get outputs
Write-Host "[+] Deployment complete!" -ForegroundColor Green
Write-Host "[*] Resources created:" -ForegroundColor Cyan
terraform output

Write-Host "[*] Next steps:" -ForegroundColor Yellow
Write-Host "  1. Your API will be available at the backend_url shown above" -ForegroundColor Gray
Write-Host "  2. Add your API keys to Azure Key Vault (see README.md)" -ForegroundColor Gray
Write-Host "  3. Test the deployment with: curl https://YOUR_BACKEND_URL/api/health/" -ForegroundColor Gray
Write-Host "  4. When idle, compute costs = 0 (scale-to-zero active)" -ForegroundColor Gray
Write-Host ""
Write-Host "[*] Credit usage:" -ForegroundColor Yellow
Write-Host "  - Your GitHub Student Pack Azure credits allocated" -ForegroundColor Gray
Write-Host "  - To stop charges: terraform destroy" -ForegroundColor Gray
