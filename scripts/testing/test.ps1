# Quick Test Script for VeriRAG
# Run this after starting Docker and Django to verify everything works

Write-Host "🧪 VeriRAG System Test Suite" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$BACKEND_URL = "http://localhost:8000"
$FRONTEND_URL = "http://localhost:5173"
$tests_passed = 0
$tests_failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedStatus = "200"
    )
    
    Write-Host "Testing: $Name..." -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host " ✅ PASS" -ForegroundColor Green
            $script:tests_passed++
            return $true
        } else {
            Write-Host " ❌ FAIL (Status: $($response.StatusCode))" -ForegroundColor Red
            $script:tests_failed++
            return $false
        }
    } catch {
        Write-Host " ❌ FAIL (Error: $($_.Exception.Message))" -ForegroundColor Red
        $script:tests_failed++
        return $false
    }
}

function Test-DockerService {
    param([string]$ServiceName)
    
    Write-Host "Checking Docker service: $ServiceName..." -NoNewline
    $status = docker inspect -f '{{.State.Running}}' $ServiceName 2>$null
    if ($status -eq "true") {
        Write-Host " ✅ Running" -ForegroundColor Green
        $script:tests_passed++
        return $true
    } else {
        Write-Host " ❌ Not Running" -ForegroundColor Red
        $script:tests_failed++
        return $false
    }
}

# ============================================================================
# 1. DOCKER SERVICES
# ============================================================================
Write-Host "`n📦 Testing Docker Services..." -ForegroundColor Yellow
Test-DockerService "rag-vault"
Test-DockerService "rag-db"
Test-DockerService "rag-redis"
Test-DockerService "rag-backend"
Test-DockerService "rag-celery-worker"

# ============================================================================
# 2. VAULT STATUS
# ============================================================================
Write-Host "`n🔐 Testing Vault Status..." -ForegroundColor Yellow
Write-Host "Checking Vault seal status..." -NoNewline
try {
    $vaultStatus = docker exec rag-vault vault status 2>&1
    if ($vaultStatus -match "Sealed\s+false") {
        Write-Host " ✅ Unsealed" -ForegroundColor Green
        $tests_passed++
    } else {
        Write-Host " ⚠️  Sealed (run unseal commands)" -ForegroundColor Yellow
        $tests_failed++
    }
} catch {
    Write-Host " ❌ Cannot check Vault" -ForegroundColor Red
    $tests_failed++
}

# ============================================================================
# 3. BACKEND ENDPOINTS
# ============================================================================
Write-Host "`n🔧 Testing Backend Endpoints..." -ForegroundColor Yellow
Test-Endpoint "Health Check" "$BACKEND_URL/api/health/"
Test-Endpoint "Swagger UI" "$BACKEND_URL/api/schema/swagger-ui/"
Test-Endpoint "Prometheus Metrics" "$BACKEND_URL/metrics"

# ============================================================================
# 4. FRONTEND
# ============================================================================
Write-Host "`n🎨 Testing Frontend..." -ForegroundColor Yellow
Test-Endpoint "React App" "$FRONTEND_URL"

# ============================================================================
# 5. PYTHON DEPENDENCIES
# ============================================================================
Write-Host "`n📦 Checking Python Dependencies..." -ForegroundColor Yellow
$required_packages = @("redis", "prometheus_client", "hvac", "django", "djangorestframework")

foreach ($pkg in $required_packages) {
    Write-Host "Checking $pkg..." -NoNewline
    $check = pip show $pkg 2>$null
    if ($check) {
        Write-Host " ✅ Installed" -ForegroundColor Green
        $tests_passed++
    } else {
        Write-Host " ❌ Missing (run: pip install $pkg)" -ForegroundColor Red
        $tests_failed++
    }
}

# ============================================================================
# 6. BACKEND UNIT TESTS (if pytest available)
# ============================================================================
Write-Host "`n🧪 Running Backend Unit Tests..." -ForegroundColor Yellow
$pytest_check = pip show pytest 2>$null
if ($pytest_check) {
    Write-Host "Running pytest..." -ForegroundColor Cyan
    Push-Location "backend"
    $test_result = pytest tests/ -v --tb=short 2>&1
    Pop-Location
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ All backend tests passed!" -ForegroundColor Green
        $tests_passed += 10  # Assume ~10 tests
    } else {
        Write-Host "❌ Some backend tests failed" -ForegroundColor Red
        Write-Host $test_result
        $tests_failed += 5
    }
} else {
    Write-Host "⚠️  pytest not installed (run: pip install pytest pytest-django)" -ForegroundColor Yellow
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "📊 Test Results Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Passed: $tests_passed" -ForegroundColor Green
Write-Host "❌ Failed: $tests_failed" -ForegroundColor Red
Write-Host ""

if ($tests_failed -eq 0) {
    Write-Host "🎉 All tests passed! System is operational." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Open browser: http://localhost:5173" -ForegroundColor White
    Write-Host "  2. Login with your credentials" -ForegroundColor White
    Write-Host "  3. Upload a PDF document" -ForegroundColor White
    Write-Host "  4. Query the AI Librarian" -ForegroundColor White
    exit 0
} else {
    Write-Host "⚠️  Some tests failed. Please check the errors above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common Fixes:" -ForegroundColor Cyan
    Write-Host "  - Docker not running: docker-compose up -d" -ForegroundColor White
    Write-Host "  - Vault sealed: Run unseal commands from docs\guides\TEST_GUIDE.md" -ForegroundColor White
    Write-Host "  - Missing packages: pip install -r apps/backend/requirements.txt" -ForegroundColor White
    Write-Host "  - Django not running: cd backend && python manage.py runserver" -ForegroundColor White
    Write-Host "  - Frontend not running: cd frontend && npm run dev" -ForegroundColor White
    exit 1
}
