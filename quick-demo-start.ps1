#!/usr/bin/env pwsh
###############################################################################
# VeriRAG Quick Demo Setup
# One-command setup for live demonstrations
###############################################################################

param(
    [switch]$SkipVault,
    [switch]$Fast
)

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🚀 VeriRAG Quick Demo Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = $PSScriptRoot
$ErrorActionPreference = "Stop"

# ============================================================================
# Step 1: Docker Services
# ============================================================================

Write-Host "[1/5] Starting Docker Services..." -ForegroundColor Yellow

$running = docker ps --format "{{.Names}}" 2>$null
if ($running -match "rag-backend") {
    Write-Host "  ✅ Services already running" -ForegroundColor Green
} else {
    Write-Host "  Starting docker-compose..." -ForegroundColor Cyan
    docker-compose up -d
    
    if ($Fast) {
        Write-Host "  ⏳ Fast mode: waiting 30s..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
    } else {
        Write-Host "  ⏳ Waiting 45s for services to initialize..." -ForegroundColor Gray
        Start-Sleep -Seconds 45
    }
}

Write-Host ""

# ============================================================================
# Step 2: Vault Setup
# ============================================================================

if (-not $SkipVault) {
    Write-Host "[2/5] Checking Vault..." -ForegroundColor Yellow
    
    $vaultStatus = docker exec rag-vault vault status 2>&1
    
    if ($vaultStatus -match "Sealed\s+false") {
        Write-Host "  ✅ Vault already unsealed" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Vault is sealed or uninitialized" -ForegroundColor Yellow
        Write-Host "  Run: ./init_vault.ps1 (requires API keys)" -ForegroundColor Cyan
        Write-Host "  Or use -SkipVault to continue without Vault" -ForegroundColor Gray
        Write-Host ""
        
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y") {
            Write-Host "  Exiting. Setup Vault first." -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "[2/5] Skipping Vault (will use environment variables)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 3: Database Setup
# ============================================================================

Write-Host "[3/5] Setting Up Database..." -ForegroundColor Yellow

# Check if Python venv exists
if (-not (Test-Path "$PROJECT_ROOT\.venv\Scripts\Activate.ps1")) {
    Write-Host "  Creating Python virtual environment..." -ForegroundColor Cyan
    Push-Location $PROJECT_ROOT
    python -m venv .venv
    Pop-Location
}

# Activate venv
Write-Host "  Activating Python environment..." -ForegroundColor Cyan
& "$PROJECT_ROOT\.venv\Scripts\Activate.ps1"

# Run migrations
Push-Location "$PROJECT_ROOT\backend"

Write-Host "  Running Django migrations..." -ForegroundColor Cyan
python manage.py migrate --noinput 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Migrations complete" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Migration warnings (may be OK)" -ForegroundColor Yellow
}

# Setup pgvector
Write-Host "  Setting up pgvector..." -ForegroundColor Cyan
python setup_pgvector.py 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ pgvector ready" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  pgvector may already be enabled" -ForegroundColor Yellow
}

Pop-Location

Write-Host ""

# ============================================================================
# Step 4: Health Check
# ============================================================================

Write-Host "[4/5] Running Health Checks..." -ForegroundColor Yellow

& "$PROJECT_ROOT\demo-health-check.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  ⚠️  Some health checks failed. See above for details." -ForegroundColor Yellow
    Write-Host ""
    
    $continue = Read-Host "Continue to launch demo? (y/N)"
    if ($continue -ne "y") {
        Write-Host "  Exiting. Fix issues first." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# ============================================================================
# Step 5: Launch Demo
# ============================================================================

Write-Host "[5/5] Launching Demo Interface..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  📊 Opening Dashboard..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

# Try to open frontend
try {
    # Check if Vite dev server is running
    $viteRunning = Get-Process | Where-Object { $_.ProcessName -eq "node" -and $_.CommandLine -like "*vite*" }
    
    if ($viteRunning) {
        Start-Process "http://localhost:5173"
        Write-Host "  ✅ Frontend: http://localhost:5173" -ForegroundColor Green
    } else {
        # Check if nginx is serving
        $response = Invoke-WebRequest -Uri "http://localhost:8080" -Method Head -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Start-Process "http://localhost:8080"
            Write-Host "  ✅ Frontend: http://localhost:8080" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Frontend not running. Start with: cd frontend && npm run dev" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  ⚠️  Could not auto-open frontend" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  📈 Prometheus: http://localhost:9090" -ForegroundColor Gray
Write-Host "  📊 Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Gray
Write-Host "  🔧 Backend API: http://localhost:8000/api/" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# Demo Quick Reference
# ============================================================================

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ DEMO READY!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick Demo Flow:" -ForegroundColor Yellow
Write-Host "    1. Upload a PDF document (Dashboard → Upload)" -ForegroundColor Gray
Write-Host "    2. Wait for Celery ingestion (~10-30 seconds)" -ForegroundColor Gray
Write-Host "    3. Ask a question about the document" -ForegroundColor Gray
Write-Host "    4. Show faithfulness score and sources" -ForegroundColor Gray
Write-Host "    5. Open Prometheus to show metrics" -ForegroundColor Gray
Write-Host ""
Write-Host "  System Commands:" -ForegroundColor Yellow
Write-Host "    View Logs:     docker-compose logs -f rag-backend" -ForegroundColor Gray
Write-Host "    View Workers:  docker-compose logs -f rag-celery-worker" -ForegroundColor Gray
Write-Host "    Restart All:   docker-compose restart" -ForegroundColor Gray
Write-Host "    Stop All:      docker-compose down" -ForegroundColor Gray
Write-Host ""
Write-Host "  📚 Full Demo Guide: See DEMO_GUIDE.md" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Keep terminal open
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
