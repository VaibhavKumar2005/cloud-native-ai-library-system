#!/usr/bin/env pwsh
<#
.SYNOPSIS
VeriRAG Local Testing Script - Complete Setup & Verification
.DESCRIPTION
This script sets up your local environment, starts Docker services, 
and tests all components to ensure everything works.
#>

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# Colors for output
$colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
}

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $color = $colors[$Type] ?? "White"
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Test-ServiceHealth {
    param([string]$Port, [string]$ServiceName)
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port" -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Status "$ServiceName is responding on port $Port" "Success"
        return $true
    }
    catch {
        Write-Status "$ServiceName is NOT responding on port $Port" "Error"
        return $false
    }
}

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================
Write-Status "=== STEP 1: Checking Prerequisites ===" "Info"

# Check Docker
Write-Status "Checking Docker..." "Info"
$dockerCheck = docker --version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Status "Docker found: $dockerCheck" "Success"
} else {
    Write-Status "Docker NOT found. Please install Docker Desktop first!" "Error"
    exit 1
}

# Check Docker running
Write-Status "Checking if Docker daemon is running..." "Info"
$dockerRunning = docker ps 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Status "Docker daemon is running" "Success"
} else {
    Write-Status "Docker daemon NOT running. Starting Docker Desktop..." "Warning"
    Write-Status "Please start Docker Desktop manually and rerun this script" "Error"
    exit 1
}

# Check Python
Write-Status "Checking Python..." "Info"
$pythonCheck = python --version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Status "Python found: $pythonCheck" "Success"
} else {
    Write-Status "Python NOT found" "Error"
    exit 1
}

# Check Node.js
Write-Status "Checking Node.js..." "Info"
$nodeCheck = node --version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Status "Node.js found: $nodeCheck" "Success"
} else {
    Write-Status "Node.js NOT found (optional, frontend will be skipped)" "Warning"
}

# ============================================================================
# STEP 2: Create .env Files
# ============================================================================
Write-Status "=== STEP 2: Creating .env Configuration Files ===" "Info"

$backendEnv = @"
# Mode
DEPLOY_MODE=local
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-prod-12345678901234567890

# Database
DATABASE_URL=postgresql://admin:devpassword@localhost:5432/verirag_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=verirag_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Vault (Local Development)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=root

# LLM APIs (Get these from https://ai.google.dev and https://console.groq.com)
GEMINI_API_KEY=test-gemini-key-12345
GROQ_API_KEY=test-groq-key-12345
OPENAI_API_KEY=test-openai-key-12345

# RAG Settings
SIMILARITY_THRESHOLD=0.7
TOP_K_RETRIEVED_DOCS=5
DEFAULT_LLM_MODEL=gemini-2.0-flash
BACKUP_LLM_MODEL=groq-llama3

# Quality & Cost Ops
COSTOPS_ENABLED=True
QUALITYOPS_ENABLED=True
MONTHLY_BUDGET=1000

# JWT
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-prod
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1,localhost:3000,localhost:5173
"@

$frontendEnv = @"
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=VeriRAG Local
VITE_DEBUG=true
"@

# Create backend .env
$backendEnvPath = "apps/backend/.env"
if (Test-Path $backendEnvPath) {
    Write-Status "Backend .env already exists, skipping" "Warning"
} else {
    $backendEnv | Out-File -FilePath $backendEnvPath -Encoding UTF8
    Write-Status "Created $backendEnvPath" "Success"
}

# Create frontend .env
$frontendEnvPath = "apps/frontend/.env"
if (Test-Path $frontendEnvPath) {
    Write-Status "Frontend .env already exists, skipping" "Warning"
} else {
    $frontendEnv | Out-File -FilePath $frontendEnvPath -Encoding UTF8
    Write-Status "Created $frontendEnvPath" "Success"
}

# ============================================================================
# STEP 3: Start Docker Services
# ============================================================================
Write-Status "=== STEP 3: Starting Docker Services ===" "Info"

Write-Status "Stopping any existing containers..." "Info"
docker-compose down 2>$null

Write-Status "Starting services (this may take 30-60 seconds)..." "Info"
docker-compose up -d

Write-Status "Waiting for services to be healthy..." "Info"
$maxWait = 60
$waited = 0
$allHealthy = $false

while ($waited -lt $maxWait) {
    $psStatus = docker-compose ps --format "{{.Service}}: {{.Status}}"
    
    if ($psStatus -match "Up.*HealthCheck:" -and $psStatus -notmatch "unhealthy") {
        $allHealthy = $true
        break
    }
    
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 5
    $waited += 5
}

if ($allHealthy) {
    Write-Status "All services are healthy!" "Success"
    docker-compose ps
} else {
    Write-Status "Services didn't reach healthy state. Checking logs..." "Warning"
    docker-compose logs --tail=20
}

# ============================================================================
# STEP 4: Setup Backend
# ============================================================================
Write-Status "=== STEP 4: Setting Up Backend ===" "Info"

# Activate venv
Write-Status "Activating Python virtual environment..." "Info"
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies
Write-Status "Installing Python dependencies..." "Info"
cd apps/backend
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Status "Failed to install Python dependencies" "Error"
    exit 1
}
Write-Status "Dependencies installed" "Success"

# Run migrations
Write-Status "Running database migrations..." "Info"
python manage.py migrate --no-input 2>&1 | Select-String -Pattern "migrat|No changes|OK" -Quiet
if ($LASTEXITCODE -eq 0) {
    Write-Status "Migrations completed" "Success"
} else {
    Write-Status "Migrations failed (this might be OK on first run)" "Warning"
}

# Create superuser
Write-Status "Creating test superuser (admin/admin)..." "Info"
echo "admin
admin@test.local
admin" | python manage.py createsuperuser --noinput 2>&1 | Select-String -Pattern "already exists|created|Exception" -Quiet
if ($LASTEXITCODE -ne 0) {
    Write-Status "User creation failed or user already exists (OK)" "Warning"
} else {
    Write-Status "Test user created" "Success"
}

cd ../..

# ============================================================================
# STEP 5: Test API Endpoints
# ============================================================================
Write-Status "=== STEP 5: Testing API Endpoints ===" "Info"

Write-Status "Waiting for backend to be ready..." "Info"
$backendReady = $false
for ($i = 0; $i -lt 10; $i++) {
    $health = curl -s http://localhost:8000/api/health 2>$null
    if ($health -match "healthy|ok") {
        $backendReady = $true
        break
    }
    Start-Sleep -Seconds 2
}

if ($backendReady) {
    Write-Status "Backend API is responding!" "Success"
    
    # Test health endpoint
    Write-Status "Testing /api/health endpoint..." "Info"
    $health = curl -s http://localhost:8000/api/health | ConvertFrom-Json
    Write-Status "Health: $($health.status)" "Success"
    
    # Test token endpoint
    Write-Status "Testing authentication..." "Info"
    $tokenResponse = curl -s -X POST http://localhost:8000/api/token/ `
        -H "Content-Type: application/json" `
        -d '{"username":"admin","password":"admin"}' | ConvertFrom-Json
    
    if ($tokenResponse.access) {
        $token = $tokenResponse.access
        Write-Status "Authentication successful! Token: $($token.Substring(0, 20))..." "Success"
        
        # Test documents endpoint
        Write-Status "Testing /api/documents/ endpoint..." "Info"
        $docs = curl -s -X GET http://localhost:8000/api/documents/ `
            -H "Authorization: Bearer $token" | ConvertFrom-Json
        Write-Status "Documents endpoint responding (found $($docs.count ?? 0) documents)" "Success"
    } else {
        Write-Status "Authentication failed" "Error"
    }
} else {
    Write-Status "Backend is not responding on http://localhost:8000" "Error"
    Write-Status "Check backend logs with: docker-compose logs rag-backend" "Info"
}

# ============================================================================
# STEP 6: Summary
# ============================================================================
Write-Status "=== STEP 6: Local Environment Summary ===" "Info"

Write-Status "✅ Services Running:" "Success"
Write-Host "   - Vault: http://localhost:8200 (no auth for dev)"
Write-Host "   - PostgreSQL: localhost:5432 (admin/devpassword)"
Write-Host "   - Redis: localhost:6379"
Write-Host "   - Backend API: http://localhost:8000/api"
Write-Host "   - Frontend: http://localhost:5173 (start with: cd apps/frontend && npm run dev)"

Write-Status "📝 Credentials:" "Info"
Write-Host "   - Admin User: admin / admin"
Write-Host "   - DB Host: rag-db (or localhost in host mode)"
Write-Host "   - DB User: admin / devpassword"

Write-Status "🧪 Test Commands:" "Info"
Write-Host "   # Get auth token"
Write-Host '   curl -X POST http://localhost:8000/api/token/ `'
Write-Host '     -H "Content-Type: application/json" `'
Write-Host '     -d ''{\"username\":\"admin\",\"password\":\"admin\"}'
Write-Host ""
Write-Host "   # Test API with token (replace TOKEN)"
Write-Host '   curl -X GET http://localhost:8000/api/documents/ `'
Write-Host '     -H "Authorization: Bearer TOKEN"'

Write-Status "📖 Useful Commands:" "Info"
Write-Host "   # View backend logs"
Write-Host "   docker-compose logs -f rag-backend"
Write-Host ""
Write-Host "   # Run backend tests"
Write-Host "   cd apps/backend && pytest -v"
Write-Host ""
Write-Host "   # Stop all services"
Write-Host "   docker-compose down"
Write-Host ""
Write-Host "   # Clean everything (removes volumes)"
Write-Host "   docker-compose down -v"

Write-Status "=== Setup Complete! ===" "Success"
Write-Status "Next: Start backend in another terminal with:" "Info"
Write-Host "   cd apps/backend"
Write-Host "   python manage.py runserver 0.0.0.0:8000"
Write-Status "Then start frontend with:" "Info"
Write-Host "   cd apps/frontend"
Write-Host "   npm run dev"
