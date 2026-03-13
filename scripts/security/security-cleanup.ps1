#!/usr/bin/env pwsh
# Security Cleanup Script
# This script removes previously tracked sensitive files from Git while keeping them locally

Write-Host "🔒 Security Cleanup Script" -ForegroundColor Cyan
Write-Host "This script will remove sensitive documentation from Git tracking" -ForegroundColor Yellow
Write-Host ""

# Check if we're in a git repository
if (-not (Test-Path .git)) {
    Write-Host "❌ Error: Not a git repository" -ForegroundColor Red
    exit 1
}

# Files to remove from Git tracking (but keep locally)
$filesToUntrack = @(
    "SETUP_COMPLETE.md",
    "FIXES_APPLIED.md"
)

Write-Host "📋 Files to remove from Git tracking:" -ForegroundColor Yellow
foreach ($file in $filesToUntrack) {
    if (Test-Path $file) {
        Write-Host "  - $file" -ForegroundColor White
    }
}
Write-Host ""

# Ask for confirmation
$confirmation = Read-Host "Do you want to continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "❌ Aborted" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🔧 Removing files from Git tracking..." -ForegroundColor Cyan

foreach ($file in $filesToUntrack) {
    if (Test-Path $file) {
        Write-Host "  Processing: $file" -ForegroundColor White
        git rm --cached $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✅ Removed from Git tracking (file kept locally)" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  File may not be tracked or already removed" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "📝 Git status:" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "✅ Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📌 Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review the changes: git status" -ForegroundColor White
Write-Host "  2. Commit the changes: git add . && git commit -m 'Security: Remove exposed secrets and enhance security'" -ForegroundColor White
Write-Host "  3. Push to remote: git push origin main" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Important: Make sure you have created a .env file with your new API key!" -ForegroundColor Yellow
