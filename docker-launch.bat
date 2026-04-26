@echo off
REM VeriRAG Docker Quick Launch Script for Windows
REM Double-click this file to start everything!

title VeriRAG Docker Launch

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║      VeriRAG - Docker Automated Launch                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    echo Or use Chocolatey: choco install docker-desktop -y
    echo.
    pause
    exit /b 1
)

echo ✅ Docker found!
echo.

REM Try to start Docker Desktop if not running
echo Checking if Docker daemon is running...
docker ps >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Starting Docker Desktop... (please wait)
    echo.
    
    if exist "C:\Program Files\Docker\Docker\Docker.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker.exe"
        echo Waiting for Docker daemon (45 seconds)...
        timeout /t 45 /nobreak
    ) else (
        echo Could not find Docker.exe
        echo Please start Docker Desktop manually
        pause
        exit /b 1
    )
)

REM Change to project directory
cd /d "c:\Users\vaibh\OneDrive\Desktop\Azure Cloud Native RAG"

echo.
echo Building Docker images (this may take 5-10 minutes on first run)...
echo.

docker-compose build --no-cache

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo ✅ Build complete!
echo.
echo Starting services...
echo.

docker-compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Failed to start services!
    docker-compose logs
    pause
    exit /b 1
)

echo.
echo ⏳ Waiting for services to initialize (30 seconds)...
timeout /t 30 /nobreak

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   ✅ SERVICES STARTED!                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

docker-compose ps

echo.
echo 🌐 Access your services:
echo    Frontend:    http://localhost:5173
echo    Backend API: http://localhost:8000
echo    Database:    localhost:5432
echo.

echo 📚 Next steps:
echo    1. Open http://localhost:5173 in your browser
echo    2. Run: python test_rag_quick.py
echo    3. Read: RAG_EVALUATION_FRAMEWORK.md
echo.

echo 🛑 To stop services:
echo    docker-compose down
echo.

pause
