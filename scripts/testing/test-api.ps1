# VeriRAG API Test Suite
# Tests the actual running system via HTTP endpoints

Write-Host "🧪 VeriRAG API Test Suite" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

$tests_passed = 0
$tests_failed = 0

# Test 1: Docker Services
Write-Host "📦 Testing Docker Services..." -ForegroundColor Yellow
$services = @("rag-vault", "rag-db", "rag-redis", "rag-backend", "rag-celery-worker")
foreach ($service in $services) {
    $status = docker inspect -f '{{.State.Running}}' $service 2>$null
    if ($status -eq "true") {
        Write-Host "  ✅ $service is running" -ForegroundColor Green
        $tests_passed++
    } else {
        Write-Host "  ❌ $service is NOT running" -ForegroundColor Red
        $tests_failed++
    }
}

# Test 2: Health Check
Write-Host "`n🔧 Testing Backend Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health/" -Method GET
    if ($health.healthy -eq $true) {
        Write-Host "  ✅ Backend is healthy" -ForegroundColor Green
        Write-Host "     - PostgreSQL: $($health.services.postgresql.status)" -ForegroundColor Gray
        Write-Host "     - Redis: $($health.services.redis.status)" -ForegroundColor Gray
        Write-Host "     - Vault: $($health.services.vault.status)" -ForegroundColor Gray
        $tests_passed++
    } else {
        Write-Host "  ❌ Backend health check failed" -ForegroundColor Red
        $tests_failed++
    }
} catch {
    Write-Host "  ❌ Cannot reach backend: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Test 3: Authentication
Write-Host "`n🔐 Testing Authentication..." -ForegroundColor Yellow
try {
    $authBody = @{
        username = "testuser"
        password = "testpass123"
    } | ConvertTo-Json
    
    $authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/token/" -Method POST -ContentType "application/json" -Body $authBody
    
    if ($authResponse.access) {
        Write-Host "  ✅ Authentication successful" -ForegroundColor Green
        Write-Host "     - Access token received: $($authResponse.access.Substring(0,20))..." -ForegroundColor Gray
        $global:token = $authResponse.access
        $tests_passed++
    } else {
        Write-Host "  ❌ Authentication failed - no token received" -ForegroundColor Red
        $tests_failed++
    }
} catch {
    Write-Host "  ❌ Authentication error: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Test 4: System Insights
Write-Host "`n📊 Testing System Insights API..." -ForegroundColor Yellow
try {
    $headers = @{ Authorization = "Bearer $global:token" }
    $insights = Invoke-RestMethod -Uri "http://localhost:8000/api/system-insights/" -Headers $headers
    
    Write-Host "  ✅ System insights retrieved" -ForegroundColor Green
    Write-Host "     - Status: $($insights.status)" -ForegroundColor Gray
    Write-Host "     - Active Model: $($insights.metrics.active_model)" -ForegroundColor Gray
    Write-Host "     - Total Queries: $($insights.metrics.total_queries)" -ForegroundColor Gray
    Write-Host "     - Failover Recoveries: $($insights.metrics.failover_recoveries)" -ForegroundColor Gray
    Write-Host "     - Database: $($insights.infrastructure.database)" -ForegroundColor Gray
    Write-Host "     - Vault: $($insights.infrastructure.vault)" -ForegroundColor Gray
    $tests_passed++
} catch {
    Write-Host "  ❌ System insights error: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Test 5: Documents API
Write-Host "`n📄 Testing Documents API..." -ForegroundColor Yellow
try {
    $headers = @{ Authorization = "Bearer $global:token" }
    $docs = Invoke-RestMethod -Uri "http://localhost:8000/api/documents/" -Headers $headers
    
    Write-Host "  ✅ Documents retrieved" -ForegroundColor Green
    Write-Host "     - Total documents: $($docs.Count)" -ForegroundColor Gray
    
    foreach ($doc in $docs) {
        $status = if ($doc.processed) { "Indexed ✓" } else { "Processing..." }
        Write-Host "     - $($doc.title): $status" -ForegroundColor Gray
    }
    $tests_passed++
} catch {
    Write-Host "  ❌ Documents API error: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Test 6: Query API
Write-Host "`n🤖 Testing RAG Query Pipeline..." -ForegroundColor Yellow
try {
    $headers = @{ 
        Authorization = "Bearer $global:token"
        "Content-Type" = "application/json"
    }
    $queryBody = @{
        query = "What is Cilium?"
    } | ConvertTo-Json
    
    $queryResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/query/" -Method POST -Headers $headers -Body $queryBody
    
    Write-Host "  ✅ Query successful" -ForegroundColor Green
    Write-Host "     - Answer: $($queryResponse.answer.Substring(0, [Math]::Min(80, $queryResponse.answer.Length)))..." -ForegroundColor Gray
    Write-Host "     - Faithfulness Score: $($queryResponse.faithfulness_score)" -ForegroundColor Gray
    Write-Host "     - Verification Passed: $($queryResponse.verification_passed)" -ForegroundColor Gray
    Write-Host "     - Model Used: $($queryResponse.model_used)" -ForegroundColor Gray
    Write-Host "     - Context Chunks: $($queryResponse.context_chunks_used)" -ForegroundColor Gray
    $tests_passed++
} catch {
    Write-Host "  ❌ Query API error: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Test 7: Frontend
Write-Host "`n🎨 Testing Frontend..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "  ✅ Frontend is accessible at http://localhost:5173" -ForegroundColor Green
        $tests_passed++
    }
} catch {
    Write-Host "  ❌ Frontend not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $tests_failed++
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "📊 Test Results Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Passed: $tests_passed" -ForegroundColor Green
Write-Host "❌ Failed: $tests_failed" -ForegroundColor Red
Write-Host ""

if ($tests_failed -eq 0) {
    Write-Host "🎉 All tests passed! System is ready for your presentation." -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️  Some tests failed. Please review the errors above." -ForegroundColor Yellow
    exit 1
}
