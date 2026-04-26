# 🐳 Docker Setup & Launch Guide

## Step 1: Install Docker Desktop

### Option A: Download & Install
1. Go to https://www.docker.com/products/docker-desktop/
2. Download Docker Desktop for Windows
3. Run installer and follow prompts
4. Restart your computer when prompted

### Option B: Use Chocolatey (Fast)
```powershell
# Run PowerShell as Administrator
choco install docker-desktop -y
```

### Option C: Use Windows Package Manager
```powershell
winget install Docker.DockerDesktop
```

---

## Step 2: Start Docker

```powershell
# Option 1: Click Start Menu → Search "Docker Desktop" → Click
# Option 2: Command line:
Start-Process "C:\Program Files\Docker\Docker\Docker.exe"

# Wait 30-60 seconds for daemon to start
Start-Sleep -Seconds 30

# Verify Docker is ready:
docker ps
# Should show: CONTAINER ID  IMAGE  COMMAND  CREATED  STATUS  PORTS  NAMES
```

---

## Step 3: Kill Old Containers (If Any)

```powershell
# Stop all running containers
docker stop $(docker ps -q)

# Remove old images (if you deleted them)
docker image prune -a --force

# Remove old volumes
docker volume prune --force

# Verify clean slate:
docker ps -a
docker images
```

---

## Step 4: Build Fresh Images

```powershell
cd "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"

# Build all images from scratch
docker-compose build --no-cache

# This will:
# - Build rag-backend (Python 3.12 + Django)
# - Build rag-frontend (Node 22 + React + nginx)
# - Build rag-celery-worker
# - Build rag-celery-beat
# Takes ~5-10 minutes first time
```

---

## Step 5: Start All Services

```powershell
# Start everything
docker-compose up -d

# Wait for services to initialize
Start-Sleep -Seconds 15

# Check status
docker-compose ps

# Expected output:
# NAME                STATUS
# rag-backend        Up (healthy)
# rag-frontend       Up (healthy)
# rag-db             Up (healthy)
# rag-redis          Up (healthy)
# rag-vault          Up (healthy)
# rag-mongo          Up (healthy)
# rag-celery-worker  Up
# rag-celery-beat    Up
```

---

## Step 6: Verify Everything Works

```powershell
# Test backend
curl http://localhost:8000/api/health/

# Test frontend
curl http://localhost:5173/

# Both should respond (not timeout)

# Check logs
docker-compose logs rag-backend | tail -20
docker-compose logs rag-frontend | tail -20
```

---

## 🌐 Access Your System

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | Research UI |
| **Backend API** | http://localhost:8000 | REST API |
| **Prometheus** | http://localhost:9090 | Metrics |
| **pgAdmin** | http://localhost:5050 | Database UI |

---

## 🛑 Stop Everything

```powershell
docker-compose down

# Remove volumes (reset database)
docker-compose down -v
```

---

## 🔧 Useful Commands

```powershell
# View logs
docker-compose logs -f rag-backend

# Enter backend container
docker exec -it rag-backend bash

# Run migrations manually
docker exec rag-backend python manage.py migrate

# Create superuser
docker exec -it rag-backend python manage.py createsuperuser

# Access database
docker exec -it rag-db psql -U admin -d verirag_db

# Check celery tasks
docker exec rag-celery-worker celery -A rag_backend inspect active
```

---

## ⚠️ Troubleshooting

### "Docker daemon not running"
```powershell
# Start Docker Desktop:
Start-Process "C:\Program Files\Docker\Docker\Docker.exe"
Start-Sleep -Seconds 30
```

### "Port 8000 already in use"
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID 12345 /F

# Or change port in docker-compose.yml
```

### "Database connection failed"
```powershell
# Check if postgres is healthy
docker-compose ps rag-db

# Check logs
docker-compose logs rag-db

# Reset and try again
docker-compose down -v
docker-compose up -d rag-db
Start-Sleep -Seconds 10
docker-compose up -d
```

---

## 📊 Next: Run Evaluation Framework

Once everything is running:

```powershell
# Run quick test
python test_rag_quick.py

# Run full evaluation
python tests/evaluate_rag.py

# The system will test:
# - Retrieval quality
# - Answer grounding
# - Hallucination detection
# - arXiv/web paper search
```

