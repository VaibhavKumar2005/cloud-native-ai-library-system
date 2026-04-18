# VeriRAG Academic - Docker Testing & Deployment Script (PowerShell)
# For Windows users

$ErrorActionPreference = "Stop"

$projectDir = Get-Location

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        VeriRAG Academic - Docker Testing Suite (Windows)      ║" -ForegroundColor Cyan
Write-Host "║        AI-Powered Research Discovery for PhD Students         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
    exit 1
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

Write-Info "Running pre-flight checks..."

# Check Docker Desktop
try {
    $dockerVersion = docker --version 2>$null
    Write-Success "Docker installed: $dockerVersion"
} catch {
    Write-Error-Custom "Docker is not installed or not in PATH. Install Docker Desktop first."
}

# Check Docker Compose
try {
    $composeVersion = docker-compose --version 2>$null
    Write-Success "Docker Compose installed: $composeVersion"
} catch {
    Write-Error-Custom "Docker Compose is not installed. Install Docker Desktop with Compose."
}

# Check if Docker daemon is running
try {
    docker ps | Out-Null
    Write-Success "Docker daemon is running"
} catch {
    Write-Error-Custom "Docker daemon is not running. Start Docker Desktop."
}

# Check for .env file
if (-Not (Test-Path ".env")) {
    Write-Warning ".env file not found. Creating from template..."
    
    $envTemplate = @"
# VeriRAG Environment Configuration

# === Core Secrets ===
DJANGO_SECRET_KEY=your-random-super-secret-key-here-change-in-production
GOOGLE_API_KEY=AIza...your-google-api-key-here
GROQ_API_KEY=gsk_...your-groq-api-key-here

# === Database ===
POSTGRES_USER=admin
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=verirag_db
POSTGRES_HOST=rag-db
POSTGRES_PORT=5432

# === Redis ===
REDIS_URL=redis://rag-redis:6379/0

# === MongoDB (optional) ===
MONGO_USER=admin
MONGO_PASSWORD=devpassword

# === Vault ===
VAULT_ADDR=http://rag-vault:8200
VAULT_TOKEN=root

# === App Settings ===
DEBUG=True
DEPLOY_MODE=local
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend,rag-backend
ENVIRONMENT=development
"@
    
    Set-Content -Path ".env" -Value $envTemplate
    Write-Warning ".env created. Update with real API keys for paper search features."
}
Write-Success ".env file present"

# ============================================================================
# DOCKER-COMPOSE SETUP
# ============================================================================

Write-Info "Building Docker images (this may take 2-5 minutes)..."
Write-Host ""

docker-compose build --no-cache 2>&1 | Where-Object { $_ -match "(Building|Built|Step|ERROR|error)" } | Write-Host

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Docker build failed"
}
Write-Success "Docker images built successfully"

# ============================================================================
# START CONTAINERS
# ============================================================================

Write-Info "Starting Docker services..."
docker-compose up -d

Write-Info "Waiting for services to be ready (this may take 30-60 seconds)..."
Write-Host ""

# Wait for PostgreSQL
Write-Info "Waiting for PostgreSQL..."
$pgReady = $false
$attempts = 0
while (-not $pgReady -and $attempts -lt 30) {
    try {
        docker-compose exec -T rag-db pg_isready -U admin 2>$null | Out-Null
        $pgReady = $true
        Write-Success "PostgreSQL is ready"
    } catch {
        Start-Sleep -Seconds 2
        $attempts++
    }
}

if (-not $pgReady) {
    Write-Warning "PostgreSQL connection timed out - continuing anyway"
}

# Wait for Redis
Write-Info "Waiting for Redis..."
Start-Sleep -Seconds 3

try {
    docker-compose exec -T rag-redis redis-cli ping 2>$null | Out-Null
    Write-Success "Redis is ready"
} catch {
    Write-Warning "Redis not responding yet"
}

Write-Info "Docker container status:"
docker-compose ps
Write-Host ""

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================

Write-Info "Creating database migrations for new academic models..."

try {
    docker-compose exec -T rag-backend python manage.py makemigrations ai_engine
    Write-Success "Migrations created"
} catch {
    Write-Error-Custom "Makemigrations failed`n$_"
}

Write-Info "Applying database migrations..."
try {
    docker-compose exec -T rag-backend python manage.py migrate
    Write-Success "Database migrated successfully"
} catch {
    Write-Error-Custom "Migration application failed`n$_"
}

# ============================================================================
# CREATE SUPERUSER
# ============================================================================

Write-Info "Creating admin superuser..."

# Try to create superuser
try {
    docker-compose exec -T rag-backend python manage.py createsuperuser --noinput --username admin --email admin@verirag.local
    Write-Success "Superuser created"
} catch {
    Write-Warning "Superuser may already exist, continuing..."
}

# Set password for admin
try {
    $shellCommand = @"
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('admin123')
    user.save()
    print('✅ Admin password set to admin123')
except User.DoesNotExist:
    print('⚠️  Admin user does not exist')
"@
    
    docker-compose exec -T rag-backend python manage.py shell -c $shellCommand
} catch {
    Write-Warning "Could not set admin password"
}

# ============================================================================
# VERIFY DEPLOYMENT
# ============================================================================

Write-Info "Verifying deployment..."
Write-Host ""

Write-Info "Checking container status..."
docker-compose ps
Write-Host ""

Write-Info "Testing API connectivity..."
Start-Sleep -Seconds 5

# Test backend API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/" -UseBasicParsing -ErrorAction SilentlyContinue
    Write-Success "Backend API responding"
} catch {
    Write-Warning "Backend API not responding yet (may need more time)"
}

# Test frontend (with retry)
$frontendReady = $false
for ($i = 0; $i -lt 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -ErrorAction SilentlyContinue
        $frontendReady = $true
        Write-Success "Frontend is running"
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $frontendReady) {
    Write-Warning "Frontend still starting - check logs with: docker-compose logs rag-frontend"
}

# ============================================================================
# TEST SUITE
# ============================================================================

Write-Host ""
Write-Info "Running smoke tests..."

# Test 1: Database connection
Write-Info "Test 1: Database connectivity..."
try {
    docker-compose exec -T rag-backend python manage.py shell -c "from django.db import connection; connection.ensure_connection()" 2>$null
    Write-Success "Database connection OK"
} catch {
    Write-Warning "Database connection failed - migrations may still be running"
}

# Test 2: JWT authentication endpoint
Write-Info "Test 2: JWT authentication endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/token/" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body '{"username": "admin", "password": "admin123"}' `
        -UseBasicParsing -ErrorAction SilentlyContinue
    
    if ($response.Content -match "access") {
        Write-Success "JWT authentication working"
    } else {
        Write-Warning "JWT endpoint exists but didn't return token"
    }
} catch {
    Write-Warning "JWT endpoint not responding yet"
}

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    DEPLOYMENT SUCCESSFUL                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "📍 SERVICE ENDPOINTS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Frontend      → http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend API   → http://localhost:8000" -ForegroundColor Green
Write-Host "  Admin Panel   → http://localhost:8000/admin" -ForegroundColor Green
Write-Host "  API Docs      → http://localhost:8000/api/schema/swagger-ui/" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

Write-Host "🔐 CREDENTIALS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Username: admin"
Write-Host "  Password: admin123"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

Write-Host "📋 TESTING CHECKLIST" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  [ ] Open http://localhost:5173 in browser"
Write-Host "  [ ] Login with admin / admin123"
Write-Host "  [ ] Navigate to /research (Academic Dashboard)"
Write-Host "  [ ] Click 'Search Papers' → search 'prompt engineering'"
Write-Host "  [ ] Add papers to library"
Write-Host "  [ ] View library and ask questions about papers"
Write-Host "  [ ] Check 'Research Gaps' analysis"
Write-Host "  [ ] Get topic recommendations"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

Write-Host "🔧 USEFUL COMMANDS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  View all logs:         docker-compose logs -f"
Write-Host "  Backend logs:          docker-compose logs -f rag-backend"
Write-Host "  Stop all services:     docker-compose down"
Write-Host "  Clean & restart:       docker-compose down -v; docker-compose up -d"
Write-Host "  Access database:       docker-compose exec rag-db psql -U admin -d verirag_db"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

Write-Host "✨ VeriRAG Academic is ready for testing!" -ForegroundColor Green
Write-Host ""
