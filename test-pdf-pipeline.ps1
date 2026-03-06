#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive PDF Pipeline Testing Script

.DESCRIPTION
    Tests the entire VeriRAG pipeline step-by-step to identify where failures occur:
    1. Backend API health
    2. Database connectivity
    3. Vault status
    4. Document upload
    5. Celery processing
    6. Vector embedding creation
    7. Query functionality

.EXAMPLE
    .\test-pdf-pipeline.ps1
#>

$ErrorActionPreference = "Continue"
$BASE_URL = "http://localhost:8000/api"
$TEST_PDF = "test-document.pdf"

Write-Host "`n🧪 VeriRAG PDF Pipeline Test Suite" -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════════
# TEST 1: BACKEND API HEALTH
# ══════════════════════════════════════════════════════════════════
Write-Host "[1/8] Testing Backend API Health..." -ForegroundColor Yellow

try {
    $healthResponse = Invoke-RestMethod -Uri "$BASE_URL/health/" -Method Get -TimeoutSec 5
    Write-Host "  ✅ Backend Status: $($healthResponse.status)" -ForegroundColor Green
    Write-Host "     Database: $($healthResponse.database)" -ForegroundColor Gray
    Write-Host "     Vault: $($healthResponse.vault)" -ForegroundColor Gray
    Write-Host "     Redis: $($healthResponse.redis)" -ForegroundColor Gray
} catch {
    Write-Host "  ❌ Backend API unreachable: $_" -ForegroundColor Red
    Write-Host "     Fix: Ensure containers are running with 'docker-compose ps'" -ForegroundColor Yellow
    exit 1
}

# ══════════════════════════════════════════════════════════════════
# TEST 2: VAULT SECRETS CHECK
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[2/8] Checking Vault Secrets..." -ForegroundColor Yellow

$vaultCheck = docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault kv get -mount=secret myapp 2>&1
if ($LASTEXITCODE -ne 0 -or $vaultCheck -match "No value found") {
    Write-Host "  ❌ Vault not initialized!" -ForegroundColor Red
    Write-Host "     Fix: Run .\init_vault.ps1 to add API keys" -ForegroundColor Yellow
    $continueTest = Read-Host "Continue testing? (y/n)"
    if ($continueTest -ne 'y') { exit 1 }
} else {
    Write-Host "  ✅ Vault contains secrets" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# TEST 3: CREATE TEST JWT TOKEN
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[3/8] Creating Test User & JWT Token..." -ForegroundColor Yellow

# Create superuser via Django management command
$createUserCmd = @"
from django.contrib.auth.models import User
user, created = User.objects.get_or_create(username='testuser', defaults={'email': 'test@example.com'})
if created:
    user.set_password('testpass123')
    user.save()
    print('User created')
else:
    print('User exists')
"@

docker exec rag-backend python manage.py shell -c $createUserCmd 2>&1 | Out-Null

# Get JWT token
try {
    $loginPayload = @{
        username = "testuser"
        password = "testpass123"
    } | ConvertTo-Json

    $tokenResponse = Invoke-RestMethod -Uri "$BASE_URL/../api/token/" -Method Post -Body $loginPayload -ContentType "application/json"
    $token = $tokenResponse.access
    Write-Host "  ✅ JWT Token obtained" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️ JWT auth failed (continuing with token-less tests): $_" -ForegroundColor Yellow
    $token = $null
}

# ══════════════════════════════════════════════════════════════════
# TEST 4: CREATE TEST PDF
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[4/8] Creating Test PDF..." -ForegroundColor Yellow

if (-not (Test-Path $TEST_PDF)) {
    # Create a simple PDF using Python
    $createPdfScript = @"
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas('$TEST_PDF', pagesize=letter)
c.drawString(100, 750, 'VeriRAG Test Document')
c.drawString(100, 700, 'This is a test PDF for the RAG pipeline.')
c.drawString(100, 680, 'Cloud computing enables scalable AI applications.')
c.drawString(100, 660, 'Vector embeddings power semantic search.')
c.save()
print('PDF created')
"@

    docker exec rag-backend python -c $createPdfScript
    docker cp rag-backend:/app/$TEST_PDF ./$TEST_PDF
    Write-Host "  ✅ Test PDF created: $TEST_PDF" -ForegroundColor Green
} else {
    Write-Host "  ✅ Using existing test PDF: $TEST_PDF" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# TEST 5: UPLOAD PDF TO BACKEND
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[5/8] Uploading PDF to Backend..." -ForegroundColor Yellow

try {
    $headers = @{}
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }

    # Use multipart/form-data
    $boundary = [System.Guid]::NewGuid().ToString()
    $pdfBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $TEST_PDF))
    
    $bodyLines = @(
        "--$boundary",
        'Content-Disposition: form-data; name="title"',
        '',
        'Test PDF Document',
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$TEST_PDF`"",
        'Content-Type: application/pdf',
        '',
        [System.Text.Encoding]::GetEncoding('ISO-8859-1').GetString($pdfBytes),
        "--$boundary--"
    )
    
    $body = $bodyLines -join "`r`n"
    $headers["Content-Type"] = "multipart/form-data; boundary=$boundary"

    $uploadResponse = Invoke-RestMethod -Uri "$BASE_URL/documents/" -Method Post -Headers $headers -Body $body
    $documentId = $uploadResponse.id
    Write-Host "  ✅ PDF uploaded successfully (ID: $documentId)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Upload failed: $_" -ForegroundColor Red
    Write-Host "     Response: $($_.Exception.Response.StatusCode)" -ForegroundColor Gray
    
    # Try alternative upload via Docker
    Write-Host "`n  🔄 Attempting direct upload via Docker..." -ForegroundColor Yellow
    docker cp ./$TEST_PDF rag-backend:/app/media/documents/
    
    $createDocCmd = @"
from ai_engine.models import Document
from django.contrib.auth.models import User
user = User.objects.get(username='testuser')
doc = Document.objects.create(title='Test PDF', file='documents/$TEST_PDF', user=user)
print(f'Document created with ID: {doc.id}')
"@
    
    $result = docker exec rag-backend python manage.py shell -c $createDocCmd
    Write-Host "  $result" -ForegroundColor Green
    
    # Extract document ID
    if ($result -match 'ID: (\d+)') {
        $documentId = $Matches[1]
    }
}

# ══════════════════════════════════════════════════════════════════
# TEST 6: CHECK CELERY WORKER LOGS
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[6/8] Checking Celery Worker Processing..." -ForegroundColor Yellow
Write-Host "  ⏳ Waiting 5 seconds for Celery to process..." -ForegroundColor Gray

Start-Sleep -Seconds 5

$celeryLogs = docker logs rag-celery-worker --tail 30 2>&1
$hasError = $celeryLogs | Select-String -Pattern "ERROR|Traceback|Failed"
$hasSuccess = $celeryLogs | Select-String -Pattern "successfully ingested|✅|SUCCESS"

if ($hasError) {
    Write-Host "  ❌ Celery worker errors detected:" -ForegroundColor Red
    $hasError | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
} elseif ($hasSuccess) {
    Write-Host "  ✅ Celery successfully processed document" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ No clear success/error in logs. Showing last 10 lines:" -ForegroundColor Yellow
    $celeryLogs | Select-Object -Last 10 | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
}

# ══════════════════════════════════════════════════════════════════
# TEST 7: VERIFY DATABASE DOCUMENT STATUS
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[7/8] Checking Database Document Status..." -ForegroundColor Yellow

if ($documentId) {
    $checkDocCmd = @"
from ai_engine.models import Document
doc = Document.objects.get(id=$documentId)
print(f'Document: {doc.title}')
print(f'Processed: {doc.processed}')
print(f'File: {doc.file.name}')
"@

    $docStatus = docker exec rag-backend python manage.py shell -c $checkDocCmd 2>&1
    Write-Host "  $docStatus" -ForegroundColor Gray
    
    if ($docStatus -match "Processed: True") {
        Write-Host "  ✅ Document marked as processed in database" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ Document NOT marked as processed" -ForegroundColor Yellow
    }
}

# ══════════════════════════════════════════════════════════════════
# TEST 8: TEST VECTOR QUERY
# ══════════════════════════════════════════════════════════════════
Write-Host "`n[8/8] Testing Vector Query..." -ForegroundColor Yellow

try {
    $queryPayload = @{
        query = "What is cloud computing?"
    } | ConvertTo-Json

    $headers = @{ "Content-Type" = "application/json" }
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }

    $queryResponse = Invoke-RestMethod -Uri "$BASE_URL/query/" -Method Post -Headers $headers -Body $queryPayload -TimeoutSec 30
    
    Write-Host "  ✅ Query successful!" -ForegroundColor Green
    Write-Host "     Answer: $($queryResponse.answer.Substring(0, [Math]::Min(100, $queryResponse.answer.Length)))..." -ForegroundColor Gray
    Write-Host "     Verified: $($queryResponse.verification)" -ForegroundColor Gray
} catch {
    Write-Host "  ❌ Query failed: $_" -ForegroundColor Red
    Write-Host "     This could mean embeddings weren't created or Vault API keys missing" -ForegroundColor Yellow
}

# ══════════════════════════════════════════════════════════════════
# FINAL DIAGNOSTIC SUMMARY
# ══════════════════════════════════════════════════════════════════
Write-Host "`n====================================`n" -ForegroundColor Cyan
Write-Host "📊 Diagnostic Summary:" -ForegroundColor Cyan
Write-Host "`n1. Backend logs:" -ForegroundColor Yellow
Write-Host "   docker logs rag-backend --tail 50`n" -ForegroundColor White

Write-Host "2. Celery worker logs:" -ForegroundColor Yellow
Write-Host "   docker logs rag-celery-worker --tail 50`n" -ForegroundColor White

Write-Host "3. Check document list:" -ForegroundColor Yellow
Write-Host "   curl http://localhost:8000/api/documents/`n" -ForegroundColor White

Write-Host "4. Manual ingestion test:" -ForegroundColor Yellow
Write-Host "   docker exec rag-backend python manage.py shell`n" -ForegroundColor White

Write-Host "5. Check vector database:" -ForegroundColor Yellow
Write-Host "   docker exec rag-db psql -U admin -d verirag_db -c 'SELECT COUNT(*) FROM langchain_pg_embedding;'`n" -ForegroundColor White

Write-Host "✅ Test suite complete!" -ForegroundColor Green
