#!/bin/bash
# 🚀 VeriRAG Quick Setup & Test Script
# This script helps you set up and test VeriRAG locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Install from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    print_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "Install from: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose found: $(docker-compose --version)"
    
    # Check Git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        echo "Install from: https://git-scm.com/downloads"
        exit 1
    fi
    print_success "Git found: $(git --version | head -n 1)"
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed"
        exit 1
    fi
    print_success "curl found"
    
    print_success "All prerequisites satisfied!"
}

# Setup environment
setup_environment() {
    print_header "Setting Up Environment"
    
    if [ -f .env ]; then
        print_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env file"
            return
        fi
    fi
    
    if [ ! -f .env.example ]; then
        print_error ".env.example not found in current directory"
        echo "Make sure you're in the project root directory"
        exit 1
    fi
    
    cp .env.example .env
    print_success "Created .env from template"
    
    # Prompt for required API keys
    print_header "API Keys Configuration"
    echo "You need at least a Google API key for the system to work."
    echo "Get one at: https://aistudio.google.com/app/apikey"
    echo ""
    
    read -p "Enter your GOOGLE_API_KEY (or press Enter to skip for local testing): " google_key
    if [ -n "$google_key" ]; then
        sed -i.bak "s|GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$google_key|" .env
        rm -f .env.bak
        print_success "GOOGLE_API_KEY configured"
    else
        print_warning "Skipping GOOGLE_API_KEY - AI features won't work"
    fi
    
    read -p "Enter your GROQ_API_KEY (optional, press Enter to skip): " groq_key
    if [ -n "$groq_key" ]; then
        sed -i.bak "s|GROQ_API_KEY=.*|GROQ_API_KEY=$groq_key|" .env
        rm -f .env.bak
        print_success "GROQ_API_KEY configured"
    else
        print_info "Groq API key not configured (optional fallback LLM)"
    fi
    
    print_success "Environment configuration complete"
}

# Start services
start_services() {
    print_header "Starting Docker Services"
    
    print_info "Building images (this may take a few minutes on first run)..."
    docker-compose build --no-cache 2>&1 | tail -n 20
    
    print_info "Starting services..."
    docker-compose up -d
    
    print_info "Waiting for services to start (30 seconds)..."
    sleep 30
    
    # Check if services are running
    print_header "Service Status"
    docker-compose ps
    
    print_success "Services started!"
}

# Health checks
health_checks() {
    print_header "Running Health Checks"
    
    # Backend health
    print_info "Checking backend at http://localhost:8000/api/health/"
    backend_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ || echo "000")
    
    if [ "$backend_response" = "200" ]; then
        print_success "Backend health check passed (HTTP $backend_response)"
    else
        print_warning "Backend health check returned HTTP $backend_response (may still be starting up)"
        print_info "Waiting 30 more seconds..."
        sleep 30
        backend_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ || echo "000")
        if [ "$backend_response" = "200" ]; then
            print_success "Backend health check passed (HTTP $backend_response)"
        else
            print_error "Backend not responding"
        fi
    fi
    
    # Frontend health
    print_info "Checking frontend at http://localhost:5173/"
    frontend_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ || echo "000")
    
    if [ "$frontend_response" = "200" ] || [ "$frontend_response" = "304" ]; then
        print_success "Frontend health check passed (HTTP $frontend_response)"
    else
        print_warning "Frontend returned HTTP $frontend_response"
    fi
    
    # Database health
    print_info "Checking database..."
    if docker-compose exec -T rag-db pg_isready -U admin > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
    else
        print_warning "PostgreSQL may still be starting"
    fi
    
    # Redis health
    print_info "Checking Redis..."
    if docker-compose exec -T rag-redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is responding to pings"
    else
        print_warning "Redis may still be starting"
    fi
}

# Show access information
show_access_info() {
    print_header "Access Information"
    
    echo -e "${GREEN}Your VeriRAG instance is now running!${NC}\n"
    
    echo "📊 Dashboards & APIs:"
    echo "  • Frontend:        http://localhost:5173"
    echo "  • Backend API:     http://localhost:8000"
    echo "  • API Docs:        http://localhost:8000/api/schema/swagger/"
    echo "  • Admin Panel:     http://localhost:8000/admin"
    echo "  • Grafana:         http://localhost:3000"
    echo "  • Prometheus:      http://localhost:9090"
    echo ""
    
    echo "📝 Default Credentials:"
    echo "  • Django Admin:    admin / (set a password)"
    echo "  • Grafana:         admin / admin"
    echo ""
    
    echo "📋 Common Commands:"
    echo "  • View logs:       docker-compose logs -f rag-backend"
    echo "  • Stop services:   docker-compose down"
    echo "  • Restart:         docker-compose restart"
    echo "  • Clean up:        docker-compose down -v"
    echo ""
    
    echo "🧪 Testing:"
    echo "  • Test API:        curl http://localhost:8000/api/health/"
    echo "  • Test Frontend:   curl http://localhost:5173/"
    echo ""
}

# Show troubleshooting
show_troubleshooting() {
    print_header "Troubleshooting"
    
    echo "If services aren't working, try these steps:"
    echo ""
    echo "1️⃣  Check service logs:"
    echo "    docker-compose logs rag-backend"
    echo "    docker-compose logs rag-frontend"
    echo ""
    
    echo "2️⃣  Restart services:"
    echo "    docker-compose restart"
    echo ""
    
    echo "3️⃣  Check port availability:"
    echo "    # Find what's using port 8000"
    echo "    sudo lsof -i :8000"
    echo "    # Kill process"
    echo "    sudo kill -9 <PID>"
    echo ""
    
    echo "4️⃣  Clean and rebuild:"
    echo "    docker-compose down -v"
    echo "    docker-compose build --no-cache"
    echo "    docker-compose up -d"
    echo ""
}

# Main menu
main_menu() {
    clear
    print_header "🚀 VeriRAG Setup & Test"
    
    echo "Choose an option:"
    echo ""
    echo "1. Full setup (check prereqs + setup env + start services + health check)"
    echo "2. Just start services"
    echo "3. Run health checks"
    echo "4. Stop services"
    echo "5. View logs"
    echo "6. Clean and restart"
    echo "7. Exit"
    echo ""
    
    read -p "Enter your choice (1-7): " choice
    
    case $choice in
        1)
            check_prerequisites
            setup_environment
            start_services
            health_checks
            show_access_info
            ;;
        2)
            start_services
            ;;
        3)
            health_checks
            ;;
        4)
            print_header "Stopping Services"
            docker-compose down
            print_success "Services stopped"
            ;;
        5)
            print_header "Backend Logs (last 50 lines, Ctrl+C to exit)"
            docker-compose logs -f --tail=50 rag-backend
            ;;
        6)
            print_header "Cleaning and Restarting"
            docker-compose down -v
            docker-compose up -d
            sleep 30
            health_checks
            ;;
        7)
            echo "Goodbye! 👋"
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            ;;
    esac
    
    read -p "Press Enter to continue..."
    main_menu
}

# Run main menu if no arguments, otherwise run single action
if [ $# -eq 0 ]; then
    main_menu
else
    case "$1" in
        --check)
            check_prerequisites
            ;;
        --setup)
            setup_environment
            ;;
        --start)
            start_services
            ;;
        --health)
            health_checks
            ;;
        --logs)
            docker-compose logs -f rag-backend
            ;;
        --stop)
            docker-compose down
            ;;
        --full)
            check_prerequisites
            setup_environment
            start_services
            health_checks
            show_access_info
            ;;
        --help)
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Options:"
            echo "  --check          Check prerequisites only"
            echo "  --setup          Setup environment variables"
            echo "  --start          Start Docker services"
            echo "  --health         Run health checks"
            echo "  --logs           View backend logs"
            echo "  --stop           Stop Docker services"
            echo "  --full           Full setup and start"
            echo "  --help           Show this help message"
            echo ""
            echo "If no option is provided, an interactive menu will be shown"
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
fi
