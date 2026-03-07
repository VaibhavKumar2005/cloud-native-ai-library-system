$ErrorActionPreference = "Stop"

$RG_NAME="rg-verirag-demo-v2"
$LOCATION="eastus2"
$ENV_NAME="env-verirag-demo-v2"

Write-Host "🚀 Starting Azure Container Apps Deployment for VeriRAG Demo"
Write-Host "------------------------------------------------------------"

Write-Host "1. Creating Resource Group: $RG_NAME in $LOCATION..."
az group create --name $RG_NAME --location $LOCATION -o none

Write-Host "2. Creating Container Apps Environment: $ENV_NAME..."
az containerapp env create --name $ENV_NAME --resource-group $RG_NAME --location $LOCATION -o none

Write-Host "3. Getting Environment Default Domain..."
$DEFAULT_DOMAIN = az containerapp env show --name $ENV_NAME --resource-group $RG_NAME --query properties.defaultDomain -o tsv
$BACKEND_URL = "https://backend.$DEFAULT_DOMAIN"
$FRONTEND_URL = "https://frontend.$DEFAULT_DOMAIN"

Write-Host "   -> Expected Backend URL: $BACKEND_URL"
Write-Host "   -> Expected Frontend URL: $FRONTEND_URL"

Write-Host "4. Deploying PostgreSQL + Vector (pgvector) Container..."
az containerapp create `
  --name rag-db `
  --resource-group $RG_NAME `
  --environment $ENV_NAME `
  --image pgvector/pgvector:pg16 `
  --target-port 5432 `
  --exposed-port 5432 `
  --transport tcp `
  --ingress internal `
  --env-vars POSTGRES_USER=admin POSTGRES_PASSWORD=devpassword POSTGRES_DB=verirag_db `
  --query "properties.configuration.ingress.fqdn" -o tsv `
  --cpu 0.5 --memory 1.0Gi


Write-Host "5. Deploying Redis Container..."
az containerapp create `
  --name rag-redis `
  --resource-group $RG_NAME `
  --environment $ENV_NAME `
  --image redis:7-alpine `
  --target-port 6379 `
  --exposed-port 6379 `
  --transport tcp `
  --ingress internal `
  --query "properties.configuration.ingress.fqdn" -o tsv `
  --cpu 0.25 --memory 0.5Gi

Write-Host "6. Deploying Backend Application..."
# Wait a moment for DB internal domains to be ready
Start-Sleep -Seconds 5

# Set API keys from environment or prompt user
$GOOGLE_API_KEY = $env:GOOGLE_API_KEY
if ([string]::IsNullOrWhiteSpace($GOOGLE_API_KEY)) {
    $GOOGLE_API_KEY = Read-Host "🔑 Please enter your GOOGLE_API_KEY for Gemini (will not be saved)"
}

$GROQ_API_KEY = $env:GROQ_API_KEY
if ([string]::IsNullOrWhiteSpace($GROQ_API_KEY)) {
    $GROQ_API_KEY = Read-Host "🔑 Please enter your GROQ_API_KEY for Llama-3 (will not be saved)"
}

az containerapp up `
  --name backend `
  --resource-group $RG_NAME `
  --environment $ENV_NAME `
  --source ./backend `
  --ingress external `
  --target-port 8000 `
  --env-vars "POSTGRES_HOST=rag-db" "POSTGRES_PORT=5432" "POSTGRES_DB=verirag_db" "POSTGRES_USER=admin" "POSTGRES_PASSWORD=devpassword" "REDIS_URL=redis://rag-redis:6379/0" "DEPLOY_MODE=production" "DJANGO_SECRET_KEY=demo-secret-key-super-safe" "DEBUG=False" "ALLOWED_HOSTS=backend.$DEFAULT_DOMAIN" "CORS_ALLOWED_ORIGINS=$FRONTEND_URL" "GOOGLE_API_KEY=$GOOGLE_API_KEY" "GROQ_API_KEY=$GROQ_API_KEY"

Write-Host "   -> Running Django Migrations on Backend..."
az containerapp exec --name backend --resource-group $RG_NAME --command "python manage.py migrate --no-input"

Write-Host "   -> Deploying Celery Worker..."
$BACKEND_IMAGE = az containerapp show --name backend --resource-group $RG_NAME --query "properties.template.containers[0].image" -o tsv
$REGISTRY_SERVER = az containerapp show --name backend --resource-group $RG_NAME --query "properties.configuration.registries[0].server" -o tsv
$REGISTRY_USERNAME = az containerapp show --name backend --resource-group $RG_NAME --query "properties.configuration.registries[0].username" -o tsv
$SECRET_NAME = az containerapp show --name backend --resource-group $RG_NAME --query "properties.configuration.registries[0].passwordSecretRef" -o tsv
$REGISTRY_PASSWORD = az containerapp secret show --name backend --resource-group $RG_NAME --secret-name $SECRET_NAME --query "value" -o tsv

az containerapp create `
  --name celery-worker `
  --resource-group $RG_NAME `
  --environment $ENV_NAME `
  --image $BACKEND_IMAGE `
  --registry-server $REGISTRY_SERVER `
  --registry-username $REGISTRY_USERNAME `
  --registry-password $REGISTRY_PASSWORD `
  --min-replicas 1 --max-replicas 1 `
  --command 'celery' `
  --args '-A rag_backend worker -l INFO' `
  --env-vars "POSTGRES_HOST=rag-db" "POSTGRES_PORT=5432" "POSTGRES_DB=verirag_db" "POSTGRES_USER=admin" "POSTGRES_PASSWORD=devpassword" "REDIS_URL=redis://rag-redis:6379/0" "DEPLOY_MODE=production" "DJANGO_SECRET_KEY=demo-secret-key-super-safe" "DEBUG=False" "GOOGLE_API_KEY=$GOOGLE_API_KEY" "GROQ_API_KEY=$GROQ_API_KEY"

Write-Host "7. Deploying Frontend Application..."
Write-Host "   -> Injecting Backend URL into Frontend Build..."
  Set-Content -Path "./frontend/.env.production" -Value "VITE_API_URL=$BACKEND_URL"

  az containerapp up `
    --name frontend `
    --resource-group $RG_NAME `
    --environment $ENV_NAME `
    --source ./frontend `
    --ingress external `
    --target-port 8080

Write-Host "------------------------------------------------------------"
Write-Host "🎉 DEPLOYMENT SUCCESSFUL! 🎉"
Write-Host "Backend API is live at: $BACKEND_URL"
Write-Host "Frontend App is live at: $FRONTEND_URL"
Write-Host "Remember to run this command when your demo is over to avoid charges: "
Write-Host 'az group delete --name rg-verirag-demo --yes --no-wait'
