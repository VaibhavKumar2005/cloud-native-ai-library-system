# Railway Deployment Guide for VeriRAG

## 🚂 Quick Deploy to Railway (Free Tier)

Railway provides FREE hosting with:
- ✅ 500 hours/month execution time (enough for demos)
- ✅ PostgreSQL database included
- ✅ Redis included
- ✅ Auto-deploy from GitHub (CI/CD built-in!)
- ✅ Custom domains
- ✅ No credit card required for trial

---

## Step-by-Step Deployment

### 1. Create Railway Account

1. Go to: https://railway.app/
2. Click **"Start a New Project"** or **"Login"**
3. Choose **"Login with GitHub"**
4. Authorize Railway to access your repositories
5. ✅ You're now logged in!

---

### 2. Create New Project

1. Click **"New Project"**
2. Choose **"Deploy from GitHub repo"**
3. Select: **`VaibhavKumar2005/cloud-native-ai-library-system`**
4. Railway will start scanning your repository

---

### 3. Add PostgreSQL Database

1. In your project dashboard, click **"+ New"**
2. Select **"Database"**
3. Choose **"Add PostgreSQL"**
4. Railway automatically creates the database
5. ✅ Note: Connection string is auto-configured

---

### 4. Add Redis

1. Click **"+ New"** again
2. Select **"Database"**
3. Choose **"Add Redis"**
4. ✅ Railway creates Redis instance

---

### 5. Deploy Backend Service

1. Click **"+ New"**
2. Select **"GitHub Repo"**
3. Choose your repository (already connected)
4. Railway detects `backend/Dockerfile`
5. Click on the service, go to **"Settings"**
6. Set **Root Directory**: `backend`
7. Set **Dockerfile Path**: `Dockerfile`

#### Configure Backend Environment Variables

Click **"Variables"** tab and add:

```bash
# Django Settings
DJANGO_SECRET_KEY=<generate-random-key>
DEBUG=False
ALLOWED_HOSTS=*.railway.app

# Database (auto-populated by Railway)
DATABASE_URL=${{Postgres.DATABASE_URL}}
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}

# Redis (auto-populated by Railway)
REDIS_URL=${{Redis.REDIS_URL}}

# API Keys
GOOGLE_API_KEY=your-google-api-key-here
GROQ_API_KEY=your-groq-api-key-here

# Celery
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Security (can use Railway's internal secrets)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-only-token
```

---

### 6. Deploy Celery Worker

1. Click **"+ New"** → **"GitHub Repo"**
2. Same repository
3. Settings:
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `Dockerfile`
4. Go to **"Settings"** → **"Deploy"**
5. Set **Custom Start Command**: 
   ```bash
   celery -A rag_backend worker -l info
   ```
6. Copy same environment variables from Backend service

---

### 7. Deploy Frontend (Optional)

1. Click **"+ New"** → **"GitHub Repo"**
2. Settings:
   - **Root Directory**: `frontend`
   - **Dockerfile Path**: `Dockerfile`
3. Environment Variables:
   ```bash
   VITE_API_URL=https://your-backend-service.railway.app
   ```

---

## ⚡ Simpler Alternative: Docker Compose on Railway

Railway can deploy your entire `docker-compose.yml` as separate services automatically!

1. Click **"New Project"**
2. Choose **"Deploy from GitHub repo"**
3. Select your repo
4. Railway auto-detects `docker-compose.yml`
5. It creates all services automatically!
6. Just add environment variables for each service

---

## 🎯 Quick Setup (Recommended)

Since you already have Docker images on Docker Hub:

### Backend Only Deployment

1. **New Project** → **"Deploy from Docker Hub"**
2. Image: `vaibhavkumar0412/verirag-backend:latest`
3. Add PostgreSQL and Redis from Railway
4. Configure environment variables
5. ✅ Backend live in 5 minutes!

### Steps:

```bash
# 1. In Railway Dashboard
- Create project
- Add PostgreSQL database
- Add Redis database
- Deploy from Docker Hub: vaibhavkumar0412/verirag-backend:latest

# 2. Set Environment Variables
DATABASE_URL → Reference Postgres
REDIS_URL → Reference Redis  
GOOGLE_API_KEY → Your key
GROQ_API_KEY → Your key

# 3. Get Public URL
- Go to Settings → Networking
- Click "Generate Domain"
- Your backend is live at: https://xxx.railway.app
```

---

## 🔄 CI/CD on Railway

Railway automatically:
- ✅ Watches your GitHub repo
- ✅ Deploys on every push to main
- ✅ Rebuilds Docker images
- ✅ Zero configuration needed!

Every time you `git push`, Railway redeploys automatically.

---

## 💰 Free Tier Limits

- **$5 free credit/month** (more than enough for demos)
- **500 execution hours/month**
- Database: 1GB PostgreSQL + Redis
- Bandwidth: 100GB/month

**Your usage**: Backend runs on-demand, likely <50 hours/month = **FREE** ✅

---

## 📊 Monitoring

Railway Dashboard shows:
- Deployment logs
- Service metrics  
- Build history
- Environment variables

---

## 🚀 After Railway Setup

Your project will have:
- ✅ Live backend URL (accessible from anywhere)
- ✅ PostgreSQL with pgvector
- ✅ Redis for Celery
- ✅ Auto-deploy on Git push (CI/CD!)
- ✅ Free hosting

---

## Next Steps

Once deployed on Railway:

1. **Test the API**:
   ```bash
   curl https://your-backend.railway.app/api/health/
   ```

2. **Update frontend** to use Railway backend:
   ```javascript
   // frontend/src/lib/api.js
   const baseURL = 'https://your-backend.railway.app';
   ```

3. **Commit and push** - Railway auto-deploys! 🎉

---

## 📚 Resources

- Railway Docs: https://docs.railway.app/
- Railway Discord: https://discord.gg/railway
- Pricing: https://railway.app/pricing

---

## 🎓 For Academic Evaluation

Railway demonstrates:
- ✅ CI/CD pipeline (auto-deploy from GitHub)
- ✅ Container orchestration (Dockerfile deployment)
- ✅ Infrastructure as code (railway.json)
- ✅ Database management (PostgreSQL + Redis)
- ✅ Environment configuration
- ✅ Monitoring and logs

**Perfect for showing DevOps skills!**
