# Trivy Security Fix Script (PowerShell) - Phase-Based Upgrades
# Generated: 2026-04-10
# Risk Level: VERY LOW (patch releases only)
# Estimated Time: 15-20 minutes with testing
# Usage: .\fix-trivy-vulnerabilities.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔒 Trivy Security Vulnerability Remediation Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Phase 1: CRITICAL axios vulnerability
Write-Host "[PHASE 1] CRITICAL - Fixing axios SSRF vulnerability" -ForegroundColor Red
Write-Host "Impact: CVE-2025-62718 (SSRF/NO_PROXY bypass)" -ForegroundColor Yellow
Write-Host "Action: npm install axios@1.15.0 --save"
Write-Host ""
$response = Read-Host "Proceed with Phase 1? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    Push-Location "apps/frontend"
    npm install axios@1.15.0 --save
    Pop-Location
    Write-Host "✓ Phase 1 Complete: axios@1.15.0" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Skipping Phase 1" -ForegroundColor Gray
}

# Phase 2: HIGH priority picomatch fixes
Write-Host "[PHASE 2] HIGH - Fixing picomatch ReDoS vulnerabilities" -ForegroundColor Yellow
Write-Host "Impact: CVE-2026-33671, CVE-2026-33672 (ReDoS + method injection)" -ForegroundColor Yellow
Write-Host "Action: npm audit fix --audit-level=moderate"
Write-Host ""
$response = Read-Host "Proceed with Phase 2? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    Push-Location "apps/frontend"
    npm audit fix --audit-level=moderate
    Pop-Location
    Write-Host "✓ Phase 2 Complete: picomatch updated" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Skipping Phase 2" -ForegroundColor Gray
}

# Phase 3: MEDIUM priority yaml
Write-Host "[PHASE 3] MEDIUM - Fixing yaml stack overflow" -ForegroundColor Yellow
Write-Host "Impact: CVE-2026-33532 (DoS on deep nesting)" -ForegroundColor Yellow
Write-Host "Action: npm install yaml@2.8.3 --save-dev"
Write-Host ""
$response = Read-Host "Proceed with Phase 3? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    Push-Location "apps/frontend"
    npm install yaml@2.8.3 --save-dev
    Pop-Location
    Write-Host "✓ Phase 3 Complete: yaml@2.8.3" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Skipping Phase 3" -ForegroundColor Gray
}

# Phase 4: Backend Python fixes
Write-Host "[PHASE 4] Backend Python - Fixing requests library" -ForegroundColor Yellow
Write-Host "Impact: CVE-2026-25645 (temp file prediction)" -ForegroundColor Yellow
Write-Host "Action: pip install requests==2.33.0"
Write-Host ""
$response = Read-Host "Proceed with Phase 4? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    Push-Location "apps/backend"
    pip install requests==2.33.0
    Pop-Location
    Write-Host "✓ Phase 4 Complete: requests==2.33.0" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Skipping Phase 4" -ForegroundColor Gray
}

# Final validation
Write-Host "[VALIDATION] Running security scans..." -ForegroundColor Cyan
Write-Host ""
$response = Read-Host "Run trivy scan on frontend? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    trivy fs apps/frontend/ --severity CRITICAL,HIGH
}

$response = Read-Host "Run trivy scan on backend? [y/n]"
if ($response -eq 'y' -or $response -eq 'Y') {
    trivy fs apps/backend/ --severity CRITICAL,HIGH
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "✓ Security remediation complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Run test suite: npm test && pytest"
Write-Host "2. Build Docker images: docker-compose build"
Write-Host "3. Tag release: git tag v1.x.x-security-patch"
Write-Host "4. Deploy to staging first"
Write-Host "5. Monitor logs for 24 hours post-deployment"
Write-Host ""
