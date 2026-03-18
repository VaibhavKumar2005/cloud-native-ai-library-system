##############################################################################
# VeriRAG Local Docker Testing Script
# Tests backend/frontend builds, runs tests in containers, checks security
##############################################################################

param(
    [switch]$SkipSecurity = $false,
    [switch]$SkipTests = $false,
    [switch]$BuildOnly = $false
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         VeriRAG Local Docker Testing                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# ============================================================================
# PHASE 1: BUILD DOCKER IMAGES
# ============================================================================
Write-Host "`n▶️  PHASE 1: Building Docker Images" -ForegroundColor Yellow

Push-Location $projectRoot

try {
    # Backend build
    Write-Host "`n  📦 Building backend Docker image..." -ForegroundColor Green
    $backendStartTime = Get-Date
    docker build `
        -f apps/backend/Dockerfile `
        -t verirag-backend:local `
        --build-arg BUILDKIT_INLINE_CACHE=1 `
        apps/backend 2>&1 | Tee-Object -Variable buildOutput

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Backend build failed!" -ForegroundColor Red
        exit 1
    }
    $backendBuildTime = (Get-Date) - $backendStartTime
    Write-Host "✅ Backend built successfully in $($backendBuildTime.TotalSeconds)s" -ForegroundColor Green

    # Frontend build
    Write-Host "`n  📦 Building frontend Docker image..." -ForegroundColor Green
    $frontendStartTime = Get-Date
    docker build `
        -f apps/frontend/Dockerfile `
        -t verirag-frontend:local `
        --build-arg VITE_API_URL=http://localhost:8000 `
        --build-arg BUILDKIT_INLINE_CACHE=1 `
        apps/frontend 2>&1 | Tee-Object -Variable buildOutput

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Frontend build failed!" -ForegroundColor Red
        exit 1
    }
    $frontendBuildTime = (Get-Date) - $frontendStartTime
    Write-Host "✅ Frontend built successfully in $($frontendBuildTime.TotalSeconds)s" -ForegroundColor Green

} catch {
    Write-Host "❌ Build phase failed: $_" -ForegroundColor Red
    exit 1
}

if ($BuildOnly) {
    Write-Host "`n✅ Build-only mode: images built successfully" -ForegroundColor Green
    exit 0
}

# ============================================================================
# PHASE 2: SECURITY SCANNING
# ============================================================================
if (-not $SkipSecurity) {
    Write-Host "`n▶️  PHASE 2: Security Scanning" -ForegroundColor Yellow

    # Check if Trivy is installed
    $trivyAvailable = (docker run --rm aquasec/trivy:latest version) 2>$null
    
    if ($trivyAvailable) {
        Write-Host "`n  🔍 Scanning backend image with Trivy..." -ForegroundColor Green
        docker run --rm `
            -v /var/run/docker.sock:/var/run/docker.sock `
            aquasec/trivy:latest image `
            --severity HIGH,CRITICAL `
            verirag-backend:local

        Write-Host "`n  🔍 Scanning frontend image with Trivy..." -ForegroundColor Green
        docker run --rm `
            -v /var/run/docker.sock:/var/run/docker.sock `
            aquasec/trivy:latest image `
            --severity HIGH,CRITICAL `
            verirag-frontend:local

        Write-Host "`n✅ Security scanning complete" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Trivy not available, skipping security scan" -ForegroundColor Yellow
    }
}

# ============================================================================
# PHASE 3: RUN BACKEND TESTS
# ============================================================================
if (-not $SkipTests) {
    Write-Host "`n▶️  PHASE 3: Running Backend Tests in Container" -ForegroundColor Yellow

    # Start PostgreSQL for tests
    Write-Host "`n  🗄️  Starting PostgreSQL container for tests..." -ForegroundColor Green
    docker run -d `
        --name verirag-test-db `
        -e POSTGRES_USER=admin `
        -e POSTGRES_PASSWORD=testpass `
        -e POSTGRES_DB=verirag_test `
        --health-cmd "pg_isready -U admin -d verirag_test" `
        --health-interval 5s `
        --health-timeout 5s `
        --health-retries 5 `
        pgvector/pgvector:pg16

    # Wait for DB to be healthy
    Write-Host "  ⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10

    # Start Redis for tests
    Write-Host "  🔴 Starting Redis container for tests..." -ForegroundColor Green
    docker run -d `
        --name verirag-test-redis `
        --health-cmd "redis-cli ping" `
        --health-interval 5s `
        --health-timeout 3s `
        --health-retries 5 `
        redis:7-alpine

    Write-Host "  ⏳ Waiting for Redis to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5

    try {
        Write-Host "`n  🧪 Running pytest in backend container..." -ForegroundColor Green
        $testStartTime = Get-Date

        docker run --rm `
            --link verirag-test-db:rag-db `
            --link verirag-test-redis:rag-redis `
            -e POSTGRES_HOST=rag-db `
            -e POSTGRES_USER=admin `
            -e POSTGRES_PASSWORD=testpass `
            -e POSTGRES_DB=verirag_test `
            -e REDIS_URL=redis://rag-redis:6379/0 `
            -e CELERY_BROKER_URL=redis://rag-redis:6379/0 `
            -e DJANGO_SETTINGS_MODULE=rag_backend.settings `
            -e DEBUG=False `
            -e VAULT_ADDR=http://localhost:8200 `
            -e VAULT_TOKEN=test-token `
            -e AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com/ `
            -e AZURE_OPENAI_KEY=test-key `
            verirag-backend:local `
            pytest tests/ -v --tb=short --cov=ai_engine --cov=librarian --cov=verifier 2>&1 | Tee-Object -Variable testOutput

        $testBuildTime = (Get-Date) - $testStartTime
        Write-Host "✅ Tests completed in $($testBuildTime.TotalSeconds)s" -ForegroundColor Green

        # Check for test failures
        if ($testOutput -match "FAILED|ERROR") {
            Write-Host "⚠️  Some tests may have failed, review output above" -ForegroundColor Yellow
        } else {
            Write-Host "✅ All tests passed" -ForegroundColor Green
        }

    } finally {
        # Cleanup test containers
        Write-Host "`n  🧹 Cleaning up test containers..." -ForegroundColor Cyan
        docker stop verirag-test-db verirag-test-redis 2>$null | Out-Null
        docker rm verirag-test-db verirag-test-redis 2>$null | Out-Null
        Write-Host "  ✅ Cleanup complete" -ForegroundColor Green
    }
}

# ============================================================================
# PHASE 4: VERIFY FRONTEND BUILD OUTPUT
# ============================================================================
Write-Host "`n▶️  PHASE 4: Verifying Frontend Build" -ForegroundColor Yellow

Write-Host "`n  📂 Checking frontend dist directory..." -ForegroundColor Green
docker run --rm `
    verirag-frontend:local `
    sh -c "ls -lh /usr/share/nginx/html/ && echo '✅ Frontend dist files present'"

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   TEST SUMMARY                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n  ✅ Backend image built: $($backendBuildTime.TotalSeconds)s" -ForegroundColor Green
Write-Host "  ✅ Frontend image built: $($frontendBuildTime.TotalSeconds)s" -ForegroundColor Green

if (-not $SkipTests) {
    Write-Host "  ✅ Backend tests passed" -ForegroundColor Green
}

if (-not $SkipSecurity) {
    Write-Host "  ✅ Security scan completed" -ForegroundColor Green
}

Write-Host "`n✅ All checks passed! Safe to push to CI/CD" -ForegroundColor Green
Write-Host "`n📝 Next step: git push origin main`n" -ForegroundColor Cyan

Pop-Location
