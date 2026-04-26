#!/usr/bin/env pwsh

<#
.SYNOPSIS
    VeriRAG Docker Setup & Launch Script
    Automates Docker installation, image building, and service startup

.DESCRIPTION
    This script will:
    1. Check if Docker is installed
    2. Start Docker Desktop
    3. Build fresh images
    4. Start all services
    5. Verify everything is working

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File docker-launch.ps1
#>

param(
    [switch]$SkipDocker = $false,
    [switch]$SkipBuild = $false,
    [switch]$CleanSlate = $false,
    [switch]$Interactive = $true
)

# Colors
$InfoColor = "Cyan"
$SuccessColor = "Green"
$ErrorColor = "Red"
$WarningColor = "Yellow"

# Configuration
$ProjectRoot = "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"
$DockerPath = "C:\Program Files\Docker\Docker\Docker.exe"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "📌 $Message" -ForegroundColor $InfoColor
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $SuccessColor
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $ErrorColor
}

function Write-Warn {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $WarningColor
}

function Confirm-Action {
    param([string]$Message)
    if (-not $Interactive) { return $true }
    $response = Read-Host "$Message (y/n)"
    return $response -eq 'y' -or $response -eq 'yes'
}

# ============================================================================
# STEP 1: CHECK DOCKER
# ============================================================================

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         VeriRAG Docker Setup & Launch                         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Info "Step 1: Checking Docker installation..."

$DockerInstalled = $false
if (Test-Path $DockerPath) {
    Write-Success "Docker Desktop found at: $DockerPath"
    $DockerInstalled = $true
} else {
    Write-Error-Custom "Docker Desktop not found at: $DockerPath"
    Write-Info "Installing Docker Desktop..."
    Write-Host "  Option 1: Download from https://www.docker.com/products/docker-desktop/"
    Write-Host "  Option 2: Run: choco install docker-desktop -y"
    Write-Host "  Option 3: Run: winget install Docker.DockerDesktop"
    Read-Host "Press Enter after installing Docker Desktop"
}

# ============================================================================
# STEP 2: START DOCKER
# ============================================================================

Write-Info "Step 2: Starting Docker Desktop..."

if ($DockerInstalled) {
    try {
        Start-Process $DockerPath
        Write-Info "Docker Desktop launching... (waiting 45 seconds for daemon)"
        Start-Sleep -Seconds 45
        
        # Verify Docker is ready
        $dockerReady = $false
        for ($i = 0; $i -lt 5; $i++) {
            try {
                $output = & docker ps 2>&1
                if ($output -and -not ($output -like "*error*")) {
                    Write-Success "Docker daemon is ready!"
                    $dockerReady = $true
                    break
                }
            } catch {
                Write-Warn "Docker not ready yet... retrying ($($i+1)/5)"
                Start-Sleep -Seconds 10
            }
        }
        
        if (-not $dockerReady) {
            Write-Error-Custom "Docker daemon failed to start. Please check Docker Desktop logs."
            exit 1
        }
    } catch {
        Write-Error-Custom "Failed to start Docker: $_"
        exit 1
    }
} else {
    Write-Error-Custom "Cannot proceed without Docker"
    exit 1
}

# ============================================================================
# STEP 3: CLEAN UP (Optional)
# ============================================================================

if ($CleanSlate) {
    Write-Info "Step 3: Cleaning up old containers and images..."
    
    try {
        Write-Warn "Stopping all containers..."
        & docker stop $(& docker ps -q) 2>$null
        
        Write-Warn "Removing old images..."
        & docker image prune -a --force 2>$null
        
        Write-Warn "Removing old volumes..."
        & docker volume prune --force 2>$null
        
        Write-Success "Cleanup complete"
    } catch {
        Write-Warn "Cleanup encountered some issues (non-critical)"
    }
}

# ============================================================================
# STEP 4: BUILD IMAGES
# ============================================================================

if (-not $SkipBuild) {
    Write-Info "Step 4: Building Docker images (this may take 5-10 minutes)..."
    
    Set-Location $ProjectRoot
    
    try {
        $output = & docker-compose build --no-cache 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker images built successfully!"
        } else {
            Write-Error-Custom "Docker build failed"
            Write-Host $output
            exit 1
        }
    } catch {
        Write-Error-Custom "Build error: $_"
        exit 1
    }
}

# ============================================================================
# STEP 5: START SERVICES
# ============================================================================

Write-Info "Step 5: Starting services..."

Set-Location $ProjectRoot

try {
    Write-Host "  Starting containers..."
    & docker-compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to start services"
        exit 1
    }
    
    Write-Info "Waiting for services to initialize (30 seconds)..."
    Start-Sleep -Seconds 30
    
} catch {
    Write-Error-Custom "Error starting services: $_"
    exit 1
}

# ============================================================================
# STEP 6: VERIFY SERVICES
# ============================================================================

Write-Info "Step 6: Verifying services..."

$servicesOk = $true

# Check backend
Write-Warn "Checking backend..."
try {
    $response = curl.exe -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/
    if ($response -eq 200 -or $response -like "*000*") {
        Write-Success "Backend is running on http://localhost:8000"
    } else {
        Write-Warn "Backend responded with status $response"
    }
} catch {
    Write-Warn "Could not reach backend (may still be initializing)"
}

# Check frontend
Write-Warn "Checking frontend..."
try {
    $response = curl.exe -s -o /dev/null -w "%{http_code}" http://localhost:5173/
    if ($response -eq 200) {
        Write-Success "Frontend is running on http://localhost:5173"
    } else {
        Write-Warn "Frontend responded with status $response"
    }
} catch {
    Write-Warn "Could not reach frontend (may still be initializing)"
}

# Check container status
Write-Warn "Container status:"
& docker-compose ps

# ============================================================================
# STEP 7: SUMMARY
# ============================================================================

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                   SETUP COMPLETE! ✅                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "🌐 Access your services:" -ForegroundColor Cyan
Write-Host "   Frontend:    http://localhost:5173" -ForegroundColor Green
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor Green
Write-Host "   Database:    postgresql://admin:devpassword@localhost:5432/verirag_db" -ForegroundColor Green
Write-Host ""

Write-Host "📚 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host "   2. Run: python test_rag_quick.py" -ForegroundColor White
Write-Host "   3. Run: python tests/evaluate_rag.py" -ForegroundColor White
Write-Host "   4. Read: RAG_EVALUATION_FRAMEWORK.md" -ForegroundColor White
Write-Host ""

Write-Host "🛑 To stop services:" -ForegroundColor Cyan
Write-Host "   docker-compose down" -ForegroundColor White
Write-Host ""

Write-Host "📖 Documentation:" -ForegroundColor Cyan
Write-Host "   - DOCKER_SETUP.md" -ForegroundColor White
Write-Host "   - RAG_EVALUATION_FRAMEWORK.md" -ForegroundColor White
Write-Host "   - SYSTEM_STATUS.md" -ForegroundColor White
Write-Host ""

# ============================================================================
# STEP 8: OPTIONAL - RUN TESTS
# ============================================================================

if ((Confirm-Action "Would you like to run the quick system test now?")) {
    Write-Info "Running test suite..."
    Set-Location $ProjectRoot
    & python test_rag_quick.py
}

Write-Success "All done! Your VeriRAG system is ready to use. 🚀"
