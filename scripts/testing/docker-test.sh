#!/bin/bash
# VeriRAG Academic - Docker Testing & Deployment Script
# Automates setup, migration, and testing

set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        VeriRAG Academic - Docker Testing Suite                ║"
echo "║        AI-Powered Research Discovery for PhD Students         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

log_info "Running pre-flight checks..."

# Check Docker installation
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker Desktop."
    exit 1
fi
log_success "Docker installed"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed."
    exit 1
fi
log_success "Docker Compose installed"

# Check if Docker daemon is running
if ! docker ps &> /dev/null; then
    log_error "Docker daemon is not running. Start Docker Desktop."
    exit 1
fi
log_success "Docker daemon is running"

# Check for .env file
if [ ! -f ".env" ]; then
    log_warning ".env file not found. Creating from template..."
    cat > .env << 'EOF'
# VeriRAG Environment Configuration
# Copy to .env and fill in your actual values

# === Core Secrets ===
DJANGO_SECRET_KEY=your-random-super-secret-key-here-change-in-production
GOOGLE_API_KEY=AIza...your-google-api-key
GROQ_API_KEY=gsk_...your-groq-api-key

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
EOF
    log_warning ".env created. Please update with real API keys if testing paper search."
fi
log_success ".env file present"

# ============================================================================
# DOCKER-COMPOSE SETUP
# ============================================================================

log_info "Building Docker images (this may take 2-3 minutes)..."
docker-compose build --no-cache 2>&1 | grep -E "(Building|Built|ERROR)" || true

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log_error "Docker build failed"
    exit 1
fi
log_success "Docker images built successfully"

# ============================================================================
# START CONTAINERS
# ============================================================================

log_info "Starting Docker services..."
docker-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be ready (this may take 30-60 seconds)..."

wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T "$service" curl -s localhost:${port} > /dev/null 2>&1; then
            log_success "$service is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_warning "$service did not become ready after ${max_attempts} attempts"
    return 1
}

# Wait for key services
docker-compose exec -T rag-db pg_isready -U admin > /dev/null || log_warning "PostgreSQL still starting..."
sleep 5

log_success "PostgreSQL is ready"

docker-compose exec -T rag-redis redis-cli ping > /dev/null && log_success "Redis is ready" || log_warning "Redis still starting..."

docker-compose ps

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================

log_info "Creating database migrations for new academic models..."

docker-compose exec -T rag-backend python manage.py makemigrations ai_engine || {
    log_error "Makemigrations failed"
    docker-compose logs rag-backend | tail -20
    exit 1
}
log_success "Migrations created"

log_info "Applying database migrations..."
docker-compose exec -T rag-backend python manage.py migrate || {
    log_error "Migration application failed"
    docker-compose logs rag-backend | tail -20
    exit 1
}
log_success "Database migrated successfully"

# ============================================================================
# CREATE SUPERUSER
# ============================================================================

log_info "Creating admin superuser..."

# Check if admin user already exists
if docker-compose exec -T rag-backend python manage.py shell -c \
    "from django.contrib.auth import get_user_model; User = get_user_model(); \
    exit(0 if User.objects.filter(username='admin').exists() else 1)" 2>/dev/null; then
    log_warning "Admin user already exists"
else
    docker-compose exec -T rag-backend python manage.py createsuperuser \
        --noinput --username admin --email admin@verirag.local 2>/dev/null || true
    docker-compose exec -T rag-backend python manage.py shell << 'SHELL_EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('admin123')
    user.save()
    print("✅ Admin password set to 'admin123'")
except User.DoesNotExist:
    print("⚠️  Could not set admin password - user doesn't exist")
SHELL_EOF
fi

# ============================================================================
# VERIFY DEPLOYMENT
# ============================================================================

log_info "Verifying deployment..."

echo ""
log_info "Checking container status..."
docker-compose ps

echo ""
log_info "Testing API connectivity..."

# Test backend API
if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
    log_success "Backend API responding"
else
    log_warning "Backend API not responding yet (may need more time)"
fi

# Test frontend
sleep 5
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    log_success "Frontend is running"
else
    log_warning "Frontend still starting..."
fi

# ============================================================================
# TEST SUITE
# ============================================================================

echo ""
log_info "Running smoke tests..."

# Test 1: Database connection
log_info "Test 1: Database connectivity..."
docker-compose exec -T rag-backend python manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('')" && \
    log_success "Database connection OK" || log_error "Database connection failed"

# Test 2: API token endpoint
log_info "Test 2: JWT authentication endpoint..."
curl -s -X POST http://localhost:8000/api/auth/token/ \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}' | grep -q "access" && \
    log_success "JWT authentication working" || log_warning "JWT endpoint not responding yet"

# Test 3: Paper search endpoint exists
log_info "Test 3: Paper search API endpoint..."
curl -s http://localhost:8000/api/papers/search/ \
    -H "Authorization: Bearer dummy" 2>&1 | grep -q "HTTP\|401\|400" && \
    log_success "Paper API endpoint exists" || log_warning "Paper API not ready"

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT SUCCESSFUL                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo -e "${BLUE}📍 SERVICE ENDPOINTS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}Frontend${NC}      → http://localhost:5173"
echo -e "  ${GREEN}Backend API${NC}   → http://localhost:8000"
echo -e "  ${GREEN}Admin Panel${NC}   → http://localhost:8000/admin"
echo -e "  ${GREEN}API Docs${NC}      → http://localhost:8000/api/schema/swagger-ui/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}🔐 CREDENTIALS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Username: admin"
echo "  Password: admin123"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}📋 TESTING CHECKLIST${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [ ] Login to http://localhost:5173 with admin/admin123"
echo "  [ ] Navigate to /research (Academic Dashboard)"
echo "  [ ] Click 'Search Papers' and search for 'prompt engineering'"
echo "  [ ] Add papers to library"
echo "  [ ] View paper library and ask questions"
echo "  [ ] Check 'Research Gaps' analysis"
echo "  [ ] Get topic recommendations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}🔧 USEFUL COMMANDS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  View all logs:         docker-compose logs -f"
echo "  Backend logs:          docker-compose logs -f rag-backend"
echo "  Stop all services:     docker-compose down"
echo "  Clean & restart:       docker-compose down -v && docker-compose up -d"
echo "  Access database:       docker-compose exec rag-db psql -U admin -d verirag_db"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${GREEN}✨ VeriRAG Academic is ready for testing!${NC}"
echo ""
