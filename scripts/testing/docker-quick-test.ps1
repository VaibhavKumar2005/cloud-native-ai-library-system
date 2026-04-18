# VeriRAG Academic - Quick Docker Test (Windows PowerShell)

Write-Host "=============================="
Write-Host "VeriRAG Academic - Docker Test"
Write-Host "=============================="
Write-Host ""

# Check Docker
Write-Host "Checking Docker..."
try {
    docker --version 2>$null | Out-Null
    Write-Host "[OK] Docker installed"
} catch {
    Write-Host "[ERROR] Docker not found"
    exit 1
}

# Check Docker is running
Write-Host "Checking Docker daemon..."
try {
    docker ps 2>$null | Out-Null
    Write-Host "[OK] Docker daemon running"
} catch {
    Write-Host "[ERROR] Docker daemon not running"
    exit 1
}

# Start services
Write-Host ""
Write-Host "Starting Docker services..."
docker-compose up -d

Write-Host ""
Write-Host "Waiting for services to initialize (60 seconds)..."
Start-Sleep -Seconds 30

# Check services
Write-Host ""
Write-Host "Service Status:"
docker-compose ps

# Run migrations
Write-Host ""
Write-Host "Creating database migrations..."
try {
    docker-compose exec -T rag-backend python manage.py makemigrations ai_engine
    Write-Host "[OK] Migrations created"
    
    docker-compose exec -T rag-backend python manage.py migrate
    Write-Host "[OK] Database migrated"
} catch {
    Write-Host "[WARNING] Migration may need manual review"
}

# Create superuser
Write-Host ""
Write-Host "Setting up admin user..."
try {
    $setAdminCmd = @"
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@local'})
u.set_password('admin123')
u.save()
print('Admin ready: admin / admin123')
"@
    
    docker-compose exec -T rag-backend python manage.py shell -c $setAdminCmd
} catch {
    Write-Host "[WARNING] Could not set admin password"
}

# Summary
Write-Host ""
Write-Host "=============================="
Write-Host "DEPLOYMENT COMPLETE"
Write-Host "=============================="
Write-Host ""
Write-Host "Access points:"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  Admin:    http://localhost:8000/admin"
Write-Host ""
Write-Host "Credentials: admin / admin123"
Write-Host ""
Write-Host "Commands:"
Write-Host "  View logs:  docker-compose logs -f"
Write-Host "  Stop:       docker-compose down"
Write-Host "  Restart:    docker-compose up -d"
Write-Host ""
