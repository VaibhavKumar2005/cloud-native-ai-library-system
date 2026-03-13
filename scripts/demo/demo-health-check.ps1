#!/usr/bin/env pwsh
###############################################################################
# VeriRAG Demo Health Check Script
# Validates all services are ready for live demonstration
###############################################################################

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🏥 VeriRAG Demo Health Check" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = $PSScriptRoot
$allHealthy = $true

# ============================================================================
# Helper Functions
# ============================================================================

function Test-Service {
    param(
        [string]$Name,
        [scriptblock]$TestScript
    )
    
    Write-Host "  Checking $Name..." -NoNewline
    try {
        $result = & $TestScript
        if ($result) {
            Write-Host " ✅" -ForegroundColor Green
            return $true
        } else {
            Write-Host " ❌" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host " ❌ ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

# ============================================================================
# 1. Docker Infrastructure
# ============================================================================

Write-Host "📦 Docker Infrastructure" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$dockerHealthy = Test-Service "Docker Engine" {
    $null -ne (docker ps 2>$null)
}
$allHealthy = $allHealthy -and $dockerHealthy

if (-not $dockerHealthy) {
    Write-Host "  ⚠️  Docker is not running. Start Docker Desktop." -ForegroundColor Yellow
    exit 1
}

# Check required containers
$requiredContainers = @(
    "rag-backend",
    "rag-db",
    "rag-redis",
    "rag-vault",
    "rag-celery-worker"
)

$runningContainers = docker ps --format "{{.Names}}" 2>$null
foreach ($container in $requiredContainers) {
    $isRunning = $runningContainers -contains $container
    if ($isRunning) {
        Write-Host "  $container" -NoNewline
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host "  $container" -NoNewline
        Write-Host " ❌ (not running)" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""

# ============================================================================
# 2. HashiCorp Vault
# ============================================================================

Write-Host "🔐 HashiCorp Vault" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$vaultHealthy = Test-Service "Vault Status" {
    $status = docker exec rag-vault vault status 2>&1
    $status -match "Sealed\s+false" -and $status -match "Initialized\s+true"
}
$allHealthy = $allHealthy -and $vaultHealthy

if (-not $vaultHealthy) {
    Write-Host "  ⚠️  Vault is sealed or uninitialized. Run: .\scripts\setup\init_vault.ps1" -ForegroundColor Yellow
}

# Check if API keys are in Vault
$vaultSecretsHealthy = Test-Service "API Keys in Vault" {
    $secrets = docker exec rag-vault vault kv get -format=json secret/myapp 2>$null | ConvertFrom-Json
    $secrets.data.data.GOOGLE_API_KEY -and $secrets.data.data.GROQ_API_KEY
}
$allHealthy = $allHealthy -and $vaultSecretsHealthy

if (-not $vaultSecretsHealthy) {
    Write-Host "  ⚠️  API keys not found in Vault. Initialize Vault with API keys." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 3. Database (PostgreSQL + pgvector)
# ============================================================================

Write-Host "🗄️  Database" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$dbHealthy = Test-Service "PostgreSQL Connection" {
    $result = docker exec rag-db pg_isready -U admin -d verirag_db 2>$null
    $result -match "accepting connections"
}
$allHealthy = $allHealthy -and $dbHealthy

$pgvectorHealthy = Test-Service "pgvector Extension" {
    $result = docker exec rag-db psql -U admin -d verirag_db -t -c "SELECT count(*) FROM pg_extension WHERE extname='vector';" 2>$null
    $count = [int](($result | Out-String).Trim() -replace '[^0-9]', '')
    $count -eq 1
}
$allHealthy = $allHealthy -and $pgvectorHealthy

if (-not $pgvectorHealthy) {
    Write-Host "  ⚠️  pgvector not enabled. Run: python apps/backend/setup_pgvector.py" -ForegroundColor Yellow
}

# Check if documents table exists (migrations ran)
$migrationsHealthy = Test-Service "Django Migrations" {
    $result = docker exec rag-db psql -U admin -d verirag_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_name='ai_engine_document';" 2>$null
    $count = [int](($result | Out-String).Trim() -replace '[^0-9]', '')
    $count -eq 1
}
$allHealthy = $allHealthy -and $migrationsHealthy

if (-not $migrationsHealthy) {
    Write-Host "  ⚠️  Database not initialized. Run: python manage.py migrate" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 4. Redis
# ============================================================================

Write-Host "🔴 Redis" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$redisHealthy = Test-Service "Redis Connection" {
    $result = docker exec rag-redis redis-cli ping 2>$null
    $result -eq "PONG"
}
$allHealthy = $allHealthy -and $redisHealthy

Write-Host ""

# ============================================================================
# 5. Backend API
# ============================================================================

Write-Host "🚀 Backend API" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$backendHealthy = Test-Service "Health Endpoint" {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health/" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
        $response.status -eq "healthy"
    } catch {
        $false
    }
}
$allHealthy = $allHealthy -and $backendHealthy

if ($backendHealthy) {
    # Get additional health details
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health/" -Method Get -TimeoutSec 5
        
        Write-Host "    Database: " -NoNewline
        if ($health.database -eq "Connected") {
            Write-Host "$($health.database) ✅" -ForegroundColor Green
        } else {
            Write-Host "$($health.database) ⚠️" -ForegroundColor Yellow
        }
        
        Write-Host "    Vault: " -NoNewline
        if ($health.vault -eq "Unsealed") {
            Write-Host "$($health.vault) ✅" -ForegroundColor Green
        } else {
            Write-Host "$($health.vault) ⚠️" -ForegroundColor Yellow
        }
        
        Write-Host "    Redis: " -NoNewline
        if ($health.redis -eq "Available") {
            Write-Host "$($health.redis) ✅" -ForegroundColor Green
        } else {
            Write-Host "$($health.redis) ⚠️" -ForegroundColor Yellow
        }
        
    } catch {
        # Silently fail if detailed health not available
    }
} else {
    Write-Host "  ⚠️  Backend API not responding. Check logs: docker logs rag-backend" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 6. Celery Worker
# ============================================================================

Write-Host "⚙️  Celery Worker" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

$celeryHealthy = Test-Service "Worker Status" {
    $logs = docker logs rag-celery-worker --tail 20 2>&1
    $logs -match "celery@.* ready" -or $logs -match "successfully connected"
}
$allHealthy = $allHealthy -and $celeryHealthy

if (-not $celeryHealthy) {
    Write-Host "  ⚠️  Celery worker may not be ready. Check logs: docker logs rag-celery-worker" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 7. Frontend (if running locally)
# ============================================================================

Write-Host "🎨 Frontend" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check if frontend is accessible (could be via vite dev server or nginx container)
$frontendHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  Frontend (nginx)" -NoNewline
        Write-Host " ✅" -ForegroundColor Green
        $frontendHealthy = $true
    }
} catch {
    # Try Vite dev server port
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  Frontend (vite dev)" -NoNewline
            Write-Host " ✅" -ForegroundColor Green
            $frontendHealthy = $true
        }
    } catch {
        Write-Host "  Frontend" -NoNewline
        Write-Host " ⚠️  (not running locally)" -ForegroundColor Yellow
        Write-Host "    Run: cd frontend && npm run dev" -ForegroundColor Gray
    }
}

Write-Host ""

# ============================================================================
# 8. System Metrics
# ============================================================================

Write-Host "📊 System Metrics" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check Prometheus
$prometheusHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  Prometheus" -NoNewline
        Write-Host " ✅" -ForegroundColor Green
        $prometheusHealthy = $true
    }
} catch {
    Write-Host "  Prometheus" -NoNewline
    Write-Host " ⚠️  (optional)" -ForegroundColor Yellow
}

# Check Grafana
$grafanaHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  Grafana" -NoNewline
        Write-Host " ✅" -ForegroundColor Green
        $grafanaHealthy = $true
    }
} catch {
    Write-Host "  Grafana" -NoNewline
    Write-Host " ⚠️  (optional)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# 9. Quick Functional Test
# ============================================================================

Write-Host "🧪 Functional Tests" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Test document count (should have some documents if system was used before)
try {
    $docCount = docker exec rag-db psql -U admin -d verirag_db -t -c "SELECT count(*) FROM ai_engine_document;" 2>$null
    $docCount = [int]$docCount.Trim()
    Write-Host "  Documents in Database: $docCount" -ForegroundColor Gray
    
    if ($docCount -eq 0) {
        Write-Host "    ℹ️  No documents uploaded yet. Upload a PDF to test ingestion." -ForegroundColor Cyan
    } else {
        Write-Host "    ✅ System has processed $docCount document(s)" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠️  Could not query document count" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Final Summary
# ============================================================================

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($allHealthy) {
    Write-Host "  ✅ ALL SYSTEMS READY FOR DEMO!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next Steps:" -ForegroundColor Cyan
    Write-Host "    1. Open Dashboard: Start-Process 'http://localhost:8080'" -ForegroundColor Gray
    Write-Host "    2. Upload a test PDF" -ForegroundColor Gray
    Write-Host "    3. Run a test query" -ForegroundColor Gray
    Write-Host "    4. Check Prometheus: Start-Process 'http://localhost:9090'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  📚 See docs\guides\DEMO_GUIDE.md for complete demo flow" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  SOME ISSUES DETECTED" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Cyan
    Write-Host "    1. Check Docker services: docker-compose ps" -ForegroundColor Gray
    Write-Host "    2. View logs: docker-compose logs" -ForegroundColor Gray
    Write-Host "    3. Restart services: docker-compose restart" -ForegroundColor Gray
    Write-Host "    4. See docs\guides\DEMO_GUIDE.md troubleshooting section" -ForegroundColor Gray
}
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Return exit code
if ($allHealthy) { exit 0 } else { exit 1 }
