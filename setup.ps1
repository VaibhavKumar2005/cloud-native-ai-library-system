#!/usr/bin/env pwsh
# VeriRAG One-Command Setup & Fix Script
# Installs dependencies, starts services, and fixes all errors

Write-Host "🚀 VeriRAG Auto-Setup Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"

# ============================================================================
# 1. FIX PYTHON DEPENDENCIES
# ============================================================================
Write-Host "📦 Step 1: Installing Python Dependencies..." -ForegroundColor Yellow

if (Test-Path "$PROJECT_ROOT\.venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & "$PROJECT_ROOT\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "❌ Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv "$PROJECT_ROOT\.venv"
    & "$PROJECT_ROOT\.venv\Scripts\Activate.ps1"
}

Write-Host "Installing backend requirements..." -ForegroundColor Cyan
Push-Location "$PROJECT_ROOT\backend"
pip install --upgrade pip
pip install -r requirements.txt
Pop-Location

Write-Host "✅ Python dependencies installed" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 2. START DOCKER SERVICES
# ============================================================================
Write-Host "🐳 Step 2: Starting Docker Services..." -ForegroundColor Yellow

Push-Location $PROJECT_ROOT
$running = docker ps --format "{{.Names}}" 2>$null
if ($running -match "rag-vault") {
    Write-Host "Docker services already running" -ForegroundColor Cyan
} else {
    Write-Host "Starting docker-compose..." -ForegroundColor Cyan
    docker-compose up -d
    Write-Host "Waiting 30 seconds for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}
Pop-Location

Write-Host "✅ Docker services started" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 3. UNSEAL VAULT
# ============================================================================
Write-Host "🔐 Step 3: Unsealing Vault..." -ForegroundColor Yellow

$vaultStatus = docker exec rag-vault vault status 2>&1
if ($vaultStatus -match "Sealed\s+false") {
    Write-Host "Vault already unsealed" -ForegroundColor Cyan
} else {
    Write-Host "Unsealing Vault with 3 keys..." -ForegroundColor Cyan
    docker exec rag-vault vault operator unseal eYj7XpJC9nD8mVs2LkP4fGhR0wN6tQxZ | Out-Null
    docker exec rag-vault vault operator unseal zK5vN2bM9cT8wXs1JlR3fDhQ0pN7uYxA | Out-Null
    docker exec rag-vault vault operator unseal pL4wN1aK8bS7vZr0IkQ2eCgP9mM5tXyB | Out-Null
    
    $newStatus = docker exec rag-vault vault status 2>&1
    if ($newStatus -match "Sealed\s+false") {
        Write-Host "✅ Vault unsealed successfully" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Vault may still be sealed" -ForegroundColor Yellow
    }
}
Write-Host ""

# ============================================================================
# 4. RUN DJANGO MIGRATIONS
# ============================================================================
Write-Host "🗄️  Step 4: Running Django Migrations..." -ForegroundColor Yellow

Push-Location "$PROJECT_ROOT\backend"
Write-Host "Running migrations..." -ForegroundColor Cyan
python manage.py migrate --noinput

Write-Host "Setting up pgvector..." -ForegroundColor Cyan
python setup_pgvector.py
Pop-Location

Write-Host "✅ Database configured" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 5. INSTALL FRONTEND DEPENDENCIES
# ============================================================================
Write-Host "📦 Step 5: Installing Frontend Dependencies..." -ForegroundColor Yellow

Push-Location "$PROJECT_ROOT\frontend"
if (Test-Path "node_modules") {
    Write-Host "node_modules already exists, skipping..." -ForegroundColor Cyan
} else {
    Write-Host "Running npm install..." -ForegroundColor Cyan
    npm install
}
Pop-Location

Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 6. START APPLICATIONS
# ============================================================================
Write-Host "🚀 Step 6: Starting Applications..." -ForegroundColor Yellow
Write-Host ""

# Check if Django is already running
$djangoPort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($djangoPort) {
    Write-Host "⚠️  Django already running on port 8000" -ForegroundColor Yellow
} else {
    Write-Host "Starting Django server in new window..." -ForegroundColor Cyan
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PROJECT_ROOT\backend'; & '$PROJECT_ROOT\.venv\Scripts\Activate.ps1'; python manage.py runserver" -WindowStyle Normal
}

# Check if Vite is already running
$vitePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($vitePort) {
    Write-Host "⚠️  Vite already running on port 5173" -ForegroundColor Yellow
} else {
    Write-Host "Starting Vite dev server in new window..." -ForegroundColor Cyan
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PROJECT_ROOT\frontend'; npm run dev" -WindowStyle Normal
}

Write-Host ""
Write-Host "Waiting 10 seconds for servers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# ============================================================================
# 7. RUN HEALTH CHECKS
# ============================================================================
Write-Host ""
Write-Host "🏥 Step 7: Running Health Checks..." -ForegroundColor Yellow
Write-Host ""

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health/" -TimeoutSec 5
    if ($health.healthy) {
        Write-Host "✅ Backend Health Check: PASS" -ForegroundColor Green
        Write-Host "   PostgreSQL: $($health.services.postgresql.status)" -ForegroundColor White
        Write-Host "   Redis: $($health.services.redis.status)" -ForegroundColor White
        Write-Host "   Vault: $($health.services.vault.status)" -ForegroundColor White
    } else {
        Write-Host "⚠️  Backend Health Check: DEGRADED" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Backend Health Check: FAIL (Server may still be starting...)" -ForegroundColor Red
}

Write-Host ""

try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5
    if ($frontend.StatusCode -eq 200) {
        Write-Host "✅ Frontend Health Check: PASS" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend Health Check: FAIL (Server may still be starting...)" -ForegroundColor Red
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🌐 Access URLs:" -ForegroundColor Yellow
Write-Host "   Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "   Swagger:   http://localhost:8000/api/schema/swagger-ui/" -ForegroundColor White
Write-Host "   Health:    http://localhost:8000/api/health/" -ForegroundColor White
Write-Host ""

Write-Host "📝 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host "   2. Create superuser: cd backend && python manage.py createsuperuser" -ForegroundColor White
Write-Host "   3. Login and upload a PDF document" -ForegroundColor White
Write-Host "   4. Query the AI Librarian" -ForegroundColor White
Write-Host ""

Write-Host "🧪 Run Tests:" -ForegroundColor Yellow
Write-Host "   .\test.ps1" -ForegroundColor White
Write-Host ""

Write-Host "📖 Full Testing Guide:" -ForegroundColor Yellow
Write-Host "   See TEST_GUIDE.md for detailed testing instructions" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
