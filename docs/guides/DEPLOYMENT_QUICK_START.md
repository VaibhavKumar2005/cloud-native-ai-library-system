# VeriRAG Deployment Quick Start Guide

**Estimated Time:** 30 minutes (local) + 15 minutes (cloud)  
**Last Updated:** March 18, 2026

---

## 🚀 Quick Start (Choose Your Path)

### Path 1: Local Docker Compose (Fastest - 5 minutes)
```bash
# 1. Create environment file
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Verify services are running
docker-compose ps
# All services should show "healthy" or "running"

# 4. Test the app
curl http://localhost:8000/api/health/  # Backend
curl http://localhost:5173/              # Frontend (React)

# 5. Open in browser
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/api/
# Vault: http://localhost:8200 (root token: root)
```

**Cost:** $0 (uses your computer)  
**Access:** Only on your machine  
**Best for:** Development, testing, local demonstrations

---

### Path 2: Railway.app (Recommended - 15 minutes)

#### Step 1: Sign Up (2 min)
```bash
# Visit: https://railway.app
# Click "Start a New Project"
# Sign in with GitHub
# Authorize the app
```

#### Step 2: Connect Your Repository (2 min)
```bash
# On Railway dashboard:
# 1. Click "+ New Project"
# 2. Select "Deploy from GitHub repo"
# 3. Choose: VaibhavKumar2005/cloud-native-ai-library-system
# 4. Click "Deploy"
```

#### Step 3: Configure Environment Variables (5 min)
```bash
# Go to: Project → Variables → Add variable

# Add these one by one:
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
POSTGRES_PASSWORD=secure-password
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo
GROQ_API_KEY=your-groq-key
VITE_API_URL=https://your-railway-app-name.up.railway.app  # ← Will be provided

# Save all variables
```

#### Step 4: Deploy (2 min)
```bash
# Railway automatically deploys when you:
# 1. Push to main
# 2. Or click "Redeploy" in the dashboard

# Monitor deployment:
# - Click on "rag-backend" service
# - View "Deployments" tab
# - Watch logs in "Logs" section
```

#### Step 5: Get Your URL (1 min)
```bash
# After deployment completes:
# Dashboard → rag-backend → Settings → Domain
# Copy your domain: https://verirag-api-username.up.railway.app

# Your frontend will be at: https://verirag-app-username.up.railway.app
```

**Cost:** $5-20/month  
**Access:** Anyone with the URL  
**Best for:** Quick demos, client presentations, quick deployment

---

### Path 3: Azure Container Apps (Production - 1-2 hours)

#### Step 1: Prerequisites
```bash
# 1. Install Azure CLI
winget install azure-cli  # Windows
brew install azure-cli    # Mac
sudo apt install azure-cli # Linux

# 2. Login to Azure
az login

# 3. Set your subscription
az account list --query "[].{name:name, id:id}"
az account set --subscription YOUR_SUBSCRIPTION_ID

# 4. Create resource group
az group create -n rg-verirag-prod -l eastus
```

#### Step 2: Create Azure Resources
```bash
# 1. Create PostgreSQL with pgvector
az postgres flexible-server create \
  -g rg-verirag-prod \
  -n pg-verirag-prod \
  --admin-user admin \
  --admin-password YourSecurePassword123! \
  --tier Burstable \
  --sku-name Standard_B1ms

# 2. Enable pgvector extension
az postgres flexible-server parameter set \
  -g rg-verirag-prod \
  -s pg-verirag-prod \
  -n shared_preload_libraries \
  --value vector

# 3. Create Container Registry
az acr create \
  -g rg-verirag-prod \
  -n acrvechiragprod \
  --sku Basic

# 4. Get ACR login credentials
az acr credential show -n acrvechiragprod --query "{username:username, password:passwords[0].value}"

# 5. Build and push Docker images
az acr build \
  -r acrvechiragprod \
  --image verirag-backend:latest \
  --file apps/backend/Dockerfile \
  apps/backend

az acr build \
  -r acrvechiragprod \
  --image verirag-frontend:latest \
  --file apps/frontend/Dockerfile \
  apps/frontend

# 6. Create Container App Environment
az containerapp env create \
  -n verirag-env \
  -g rg-verirag-prod \
  --location eastus

# 7. Deploy backend container app
az containerapp create \
  -g rg-verirag-prod \
  -n verirag-backend \
  --environment verirag-env \
  --image acrvechiragprod.azurecr.io/verirag-backend:latest \
  --target-port 8000 \
  --ingress external \
  --environment-variables \
    DJANGO_SETTINGS_MODULE=rag_backend.settings \
    POSTGRES_HOST=pg-verirag-prod.postgres.database.azure.com \
    PYTHON_REQUIREMENTS_SATISFIED=True

# 8. Deploy frontend container app
az containerapp create \
  -g rg-verirag-prod \
  -n verirag-frontend \
  --environment verirag-env \
  --image acrvechiragprod.azurecr.io/verirag-frontend:latest \
  --target-port 8080 \
  --ingress external \
  --environment-variables \
    VITE_API_URL=https://verirag-backend.xxxxx.eastus.azurecontainerapps.io
```

#### Step 3: Configure DNS (Optional)
```bash
# Get your public URLs
az containerapp show -g rg-verirag-prod -n verirag-backend \
  --query "properties.configuration.ingress.fqdn"
# Returns: verirag-backend.xxxxx.eastus.azurecontainerapps.io

# Point your domain to this URL via DNS CNAME record
```

**Cost:** $40-100/month  
**Access:** Anyone with the URL  
**Best for:** Production, enterprise, long-term deployments

---

### Path 4: Self-Hosted VPS (30 minutes)

#### Step 1: Provision VPS
```bash
# Options:
# - DigitalOcean: $5-15/month (recommended)
# - Linode: $5-20/month
# - Scaleway: €5-15/month
# Choose 2GB RAM, Ubuntu 22.04 LTS

# Example with DigitalOcean:
# 1. Create account at digitalocean.com
# 2. Create Droplet (Ubuntu 22.04, 2GB RAM, $5/month)
# 3. SSH into droplet: ssh root@your.droplet.ip
```

#### Step 2: Setup Server
```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# 1. Update system
apt update && apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Install Docker Compose
apt install docker-compose -y

# 4. Enable and start Docker
systemctl enable docker
systemctl start docker

# 5. Verify installation
docker --version
docker-compose --version
```

#### Step 3: Deploy App
```bash
# 1. Clone repository
git clone https://github.com/VaibhavKumar2005/cloud-native-ai-library-system.git
cd cloud-native-ai-library-system

# 2. Create .env file with your configuration
nano .env
# Add: VITE_API_URL=https://your-vps-domain.com
#      AZURE_OPENAI_KEY=your-key
#      etc.

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. Setup reverse proxy (Nginx)
# Install Nginx
apt install nginx -y

# Create config
nano /etc/nginx/sites-available/verirag
# Add config (see below)

# Enable site
ln -s /etc/nginx/sites-available/verirag /etc/nginx/sites-enabled/

# Test and reload
nginx -t
systemctl reload nginx

# 6. Setup SSL certificate (Let's Encrypt)
apt install certbot python3-certbot-nginx -y
certbot certonly --standalone -d your-domain.com
# Or use: certbot --nginx -d your-domain.com
```

**Nginx Config Template:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Cost:** $5-15/month  
**Access:** Anyone with the URL  
**Best for:** Learning, full control, avoiding vendor lock-in

---

## 🧪 Local Testing Before Deployment

```bash
# 1. Ensure all services are healthy
docker-compose ps
# All should show "healthy" or "running"

# 2. Test backend health endpoint
curl http://localhost:8000/api/health/
# Should return: {"status": "healthy"}

# 3. Test frontend loads
curl http://localhost:5173/
# Should return HTML with React app

# 4. Test database connection
docker-compose exec rag-db psql -U admin -d verirag_db -c "SELECT 1;"
# Should return: (1 row)

# 5. Run test suite
docker-compose exec rag-backend python manage.py test
# Should show: OK or similar message

# 6. Upload a test PDF
curl -X POST http://localhost:8000/api/documents/ \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.pdf" \
  -F "title=Test Document"
# Should return: 201 Created with document ID

# 7. Ask a question
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "document_ids": [1]}'
# Should return: 200 OK with answer
```

---

## 🐛 Troubleshooting Deployment

### "502 Bad Gateway" after deployment
```bash
# 1. Check if backend is running
curl https://your-domain/api/health/

# 2. Check backend logs
docker-compose logs rag-backend

# 3. Check if environment variables are set
docker-compose exec rag-backend env | grep DJANGO

# 4. Restart backend
docker-compose restart rag-backend

# 5. Check health endpoint exists
docker-compose exec rag-backend python manage.py shell
>>> from django.urls import resolve
>>> resolve('/api/health/')
# Should work without error
```

### "Connection refused" to database
```bash
# 1. Check PostgreSQL is running
docker-compose ps rag-db

# 2. Check PostgreSQL credentials
docker-compose logs rag-db

# 3. Check from inside container
docker-compose exec rag-backend python -c \
  "import psycopg2; print(psycopg2.connect('postgres://admin:password@rag-db/verirag_db'))"

# 4. Check POSTGRES_HOST is correct
# In docker-compose: should be "rag-db" (service name)
# In .env: depends on deployment (localhost, IP address, or RDS endpoint)
```

### "CORS error" between frontend and backend
```bash
# 1. Check VITE_API_URL in frontend
# Should match your backend domain exactly
# Example: https://api.yourdomain.com (no trailing slash)

# 2. Check ALLOWED_HOSTS in Django
# Settings in rag_backend/settings.py should include your domain

# 3. Check CSRF token
# Make sure frontend sends X-CSRFToken header with requests

# 4. Fix in Django settings:
ALLOWED_HOSTS = ['your-domain.com', 'api.your-domain.com', 'localhost']
CORS_ALLOWED_ORIGINS = ['https://your-domain.com', 'http://localhost:5173']
```

### "API key not found" errors
```bash
# 1. Check .env file has all required keys
cat .env | grep -E "OPENAI|GROQ|AZURE"

# 2. Check environment variables are loaded
docker-compose exec rag-backend env | grep AZURE_OPENAI_KEY

# 3. If using Vault (local), check Vault is running and seeded
docker-compose logs rag-vault

# 4. For Azure Key Vault (cloud), check Azure credentials
az account show

# 5. Check Vault has the secret
docker-compose exec rag-vault vault kv get secret/myapp/GROQ_API_KEY
```

---

## 📊 Platform Comparison

| Feature | Local | Railway | Azure | Self-Hosted |
|---------|-------|---------|-------|-------------|
| **Setup Time** | 5 min | 15 min | 1-2 hrs | 30 min |
| **Monthly Cost** | $0 | $5-20 | $40-100 | $5-15 |
| **Uptime SLA** | N/A | 99.9% | 99.95% | You manage |
| **Auto-scaling** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Database included** | ✅ Container | ✅ Railway DB | Use Azure DB | Use host DB |
| **SSL/HTTPS** | ❌ Self-signed | ✅ Auto | ✅ Auto | Let's Encrypt |
| **CI/CD Integration** | ❌ Manual | ✅ Auto | ✅ Auto | ❌ Manual |
| **Learning curve** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Hard | ⭐⭐ Medium |
| **Best for** | Development | Quick demo | Enterprise | Control |

---

## ✅ Deployment Checklist

Before going live:

- [ ] `.env` file configured with all API keys
- [ ] `docker-compose up -d` works locally
- [ ] Tests pass: `pytest apps/backend/tests/`
- [ ] Frontend loads: Open http://localhost:5173 in browser
- [ ] Backend responds: `curl http://localhost:8000/api/health/`
- [ ] Can upload PDF without errors
- [ ] Can ask questions and get responses
- [ ] GitHub Actions workflow passes (all 5 stages)
- [ ] Cloud platform shows "healthy" status
- [ ] Domain CNAME points to correct IP/endpoint
- [ ] SSL certificate is valid (if using HTTPS)
- [ ] Monitoring is configured (logs, alerts)
- [ ] Team has runbook for troubleshooting
- [ ] Demo has been tested end-to-end

---

## 🎉 You're Deployed!

Once you see the green checkmarks:
- ✅ App is live at your domain
- ✅ CI/CD automatically deploys code changes
- ✅ Database is backing up (if configured)
- ✅ Monitoring is tracking errors and performance

**Next steps:**
1. Share the URL with your team
2. Get feedback on functionality
3. Monitor logs for any issues
4. Plan additional features based on usage

**Questions?** Check the troubleshooting section above or review full docs in `/docs/`

