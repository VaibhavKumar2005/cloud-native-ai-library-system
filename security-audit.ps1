#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Security Audit Script — Verify NO secrets are exposed before git push

.DESCRIPTION
    Comprehensive pre-commit security scan for VeriRAG project.
    Checks for hardcoded API keys, sensitive files, and verifies Vault setup.

.EXAMPLE
    .\security-audit.ps1
#>

Write-Host "🔒 VeriRAG Security Audit — Pre-Push Checklist" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

$issues = @()

# ══════════════════════════════════════════════════════════════════
# 1. CHECK .gitignore IS PROTECTING SENSITIVE FILES
# ══════════════════════════════════════════════════════════════════
Write-Host "[1/7] Checking .gitignore configuration..." -ForegroundColor Yellow

$requiredIgnores = @('.env', '.envrc', '*.log', '__pycache__', 'celerybeat-schedule', 'db.sqlite3')
$gitignoreContent = Get-Content .gitignore -Raw -ErrorAction SilentlyContinue

$missingIgnores = @()
foreach ($pattern in $requiredIgnores) {
    if ($gitignoreContent -notmatch [regex]::Escape($pattern)) {
        $missingIgnores += $pattern
    }
}

if ($missingIgnores.Count -gt 0) {
    $issues += "⚠️  Missing .gitignore entries: $($missingIgnores -join ', ')"
} else {
    Write-Host "  ✅ .gitignore properly configured" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 2. VERIFY .env IS NOT TRACKED BY GIT
# ══════════════════════════════════════════════════════════════════
Write-Host "[2/7] Verifying .env is not tracked..." -ForegroundColor Yellow

$trackedFiles = git ls-files | Select-String -Pattern '\.env$|\.envrc$'
if ($trackedFiles) {
    $issues += "🚨 CRITICAL: .env file is tracked by git! Run: git rm --cached .env"
} else {
    Write-Host "  ✅ .env is not tracked by git" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 3. SCAN FOR HARDCODED API KEYS IN TRACKED FILES
# ══════════════════════════════════════════════════════════════════
Write-Host "[3/7] Scanning for hardcoded API keys..." -ForegroundColor Yellow

$apiKeyPatterns = @(
    'AIza[a-zA-Z0-9_-]{35}',              # Google API Key
    'gsk_[a-zA-Z0-9]{20,}',               # Groq API Key
    'sk-[a-zA-Z0-9]{32,}',                # OpenAI API Key
    'AKIA[0-9A-Z]{16}',                   # AWS Access Key
    'ghp_[a-zA-Z0-9]{36}',                # GitHub Personal Access Token
    'xox[baprs]-[0-9]{10,}-[a-zA-Z0-9]+'  # Slack Token
)

$foundSecrets = @()
foreach ($pattern in $apiKeyPatterns) {
    $matches = git grep -E $pattern 2>$null
    if ($matches) {
        $foundSecrets += $matches
    }
}

if ($foundSecrets.Count -gt 0) {
    $issues += "🚨 CRITICAL: Potential API keys found in tracked files:`n$($foundSecrets -join "`n")"
} else {
    Write-Host "  ✅ No hardcoded API keys detected" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 4. CHECK FOR SENSITIVE ENVIRONMENT VARIABLES IN DOCKER-COMPOSE
# ══════════════════════════════════════════════════════════════════
Write-Host "[4/7] Checking docker-compose.yml for hardcoded secrets..." -ForegroundColor Yellow

$dockerComposeContent = Get-Content docker-compose.yml -Raw
$sensitivePatterns = @(
    'GOOGLE_API_KEY\s*=\s*[A-Za-z0-9]',
    'GROQ_API_KEY\s*=\s*[A-Za-z0-9]',
    'password:\s*[^${\s]'
)

$foundInDocker = @()
foreach ($pattern in $sensitivePatterns) {
    if ($dockerComposeContent -match $pattern) {
        $foundInDocker += $pattern
    }
}

if ($foundInDocker.Count -gt 0) {
    $issues += "⚠️  Potential hardcoded secrets in docker-compose.yml"
} else {
    Write-Host "  ✅ docker-compose.yml looks safe" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 5. VERIFY VAULT IS INITIALIZED (LOCAL MODE ONLY)
# ══════════════════════════════════════════════════════════════════
Write-Host "[5/7] Checking HashiCorp Vault initialization..." -ForegroundColor Yellow

$vaultCheck = docker exec -e VAULT_TOKEN=dev-only-root-token rag-vault vault kv get -mount=secret myapp 2>&1
if ($LASTEXITCODE -ne 0 -or $vaultCheck -match "No value found") {
    $issues += "⚠️  Vault not initialized. Run: .\init_vault.ps1"
} else {
    Write-Host "  ✅ Vault is initialized with secrets" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 6. CHECK FOR ACCIDENTALLY COMMITTED LARGE FILES
# ══════════════════════════════════════════════════════════════════
Write-Host "[6/7] Checking for large files..." -ForegroundColor Yellow

$largeFiles = git ls-files | ForEach-Object {
    $size = (Get-Item $_ -ErrorAction SilentlyContinue).Length
    if ($size -gt 10MB) {
        "$_ ($([math]::Round($size/1MB, 2)) MB)"
    }
}

if ($largeFiles) {
    $issues += "⚠️  Large files detected (should be in .gitignore or LFS):`n$($largeFiles -join "`n")"
} else {
    Write-Host "  ✅ No large files in git" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════
# 7. FINAL SAFETY CHECK — LIST STAGED FILES
# ══════════════════════════════════════════════════════════════════
Write-Host "[7/7] Reviewing staged files for commit..." -ForegroundColor Yellow

$stagedFiles = git diff --cached --name-only
if ($stagedFiles) {
    Write-Host "  📄 Files staged for commit:" -ForegroundColor Cyan
    $stagedFiles | ForEach-Object { Write-Host "     - $_" -ForegroundColor White }
    
    # Check if .env is accidentally staged
    if ($stagedFiles -match '\.env$') {
        $issues += "🚨 CRITICAL: .env is staged for commit! Run: git reset HEAD .env"
    }
} else {
    Write-Host "  ℹ️  No files currently staged" -ForegroundColor Gray
}

# ══════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════
Write-Host "`n================================================" -ForegroundColor Cyan
if ($issues.Count -eq 0) {
    Write-Host "✅ SECURITY AUDIT PASSED — Safe to push!" -ForegroundColor Green
    Write-Host "`nBefore pushing, ensure you've run:" -ForegroundColor Yellow
    Write-Host "  1. .\init_vault.ps1  (to populate Vault with API keys)" -ForegroundColor White
    Write-Host "  2. git status        (verify no .env or secrets)" -ForegroundColor White
    Write-Host "  3. git push          (you're good to go!)" -ForegroundColor White
    exit 0
} else {
    Write-Host "❌ SECURITY AUDIT FAILED — DO NOT PUSH YET!" -ForegroundColor Red
    Write-Host "`nIssues found:" -ForegroundColor Yellow
    $issues | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "`nFix these issues before pushing to prevent secret leaks." -ForegroundColor Yellow
    exit 1
}
