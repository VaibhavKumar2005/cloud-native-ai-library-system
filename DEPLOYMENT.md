# VeriRAG — Dual-Mode Deployment Strategy

> **AZ-400 Compliant** | **GitOps (Argo CD)** | **Scale-to-Zero** | **Zero Hardcoded Secrets**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deployment Modes](#deployment-modes)
3. [Secret Management](#secret-management)
4. [CI/CD Pipeline (GitHub Actions)](#cicd-pipeline)
5. [GitOps (Argo CD)](#gitops-argo-cd)
6. [Local Mode — Quick Start](#local-mode--quick-start)
7. [Cloud Mode — Azure Deployment](#cloud-mode--azure-deployment)
8. [Burst Mode — AKS On-Demand](#burst-mode--aks-on-demand)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                          │
│  ┌──────────┐   CI/CD    ┌──────────┐   Push    ┌─────────────┐  │
│  │  Source   ├───────────►│  GitHub  ├──────────►│   Azure     │  │
│  │  Code     │  Actions   │  Actions │  images   │   ACR       │  │
│  └──────────┘            └────┬─────┘           └──────┬──────┘  │
│                               │ update tags             │         │
│                          ┌────▼─────┐                   │         │
│                          │ K8s Mani-│                   │         │
│                          │ fests    │                   │         │
│                          │ Repo     │                   │         │
│                          └────┬─────┘                   │         │
└───────────────────────────────┼──────────────────────────┼────────┘
                                │ watch                    │ pull
                           ┌────▼─────┐              ┌────▼─────┐
                           │ Argo CD  ├──────────────►│ K8s/ACA  │
                           │          │  auto-sync    │ Cluster  │
                           └──────────┘               └──────────┘
```

---

## Deployment Modes

| Feature | Local Mode | Cloud Mode | Burst Mode |
|---------|-----------|------------|------------|
| **Orchestrator** | Kind / Minikube | Azure Container Apps | AKS (Terraform) |
| **Database** | PostgreSQL container (pgvector) | Azure PG Flexible Server | Azure PG Flexible Server |
| **Cache** | Redis container | Azure Cache for Redis | Azure Cache for Redis |
| **Secrets** | HashiCorp Vault (dev server) | Azure Key Vault | Azure Key Vault |
| **Scaling** | Manual replicas | HPA + KEDA (scale-to-zero) | KEDA + Node autoscaler (0→10) |
| **Cost** | $0 (laptop) | ~$0 idle (scale-to-zero) | Pay-per-use (destroy when done) |
| **Helm Values** | `values.yaml` | `values-production.yaml` | `values-production.yaml` |

---

## Secret Management

### The Golden Rule

> **API keys (GOOGLE_API_KEY, GROQ_API_KEY) NEVER appear in:**
> - `.env` or `.env.example`
> - Environment variables
> - Terraform state
> - Kubernetes Secrets YAML committed to Git
>
> They are stored in **HashiCorp Vault** (local) or **Azure Key Vault** (cloud)
> and fetched at runtime by `settings.py` → `get_secret()`.

### Local Mode Flow

```
┌──────────┐     hvac      ┌───────────────┐
│ Django   ├──────────────►│ HashiCorp     │
│ settings │   get_secret() │ Vault (dev)   │
│ .py      │               │ secret/myapp  │
└──────────┘               └───────────────┘
                            Seeded by init_vault.ps1
```

### Cloud Mode Flow

```
┌──────────┐  azure-identity  ┌────────────────┐
│ Django   ├─────────────────►│ Azure Key      │
│ settings │  get_secret()    │ Vault          │
│ .py      │  (DefaultAzure   │ (Managed ID)   │
└──────────┘   Credential)    └────────────────┘
                                      ▲
                               ┌──────┴──────┐
                               │ External    │
                               │ Secrets     │
                               │ Operator    │  → syncs K8s Secrets
                               └─────────────┘
```

### How `settings.py` Detects Mode

```python
DEPLOY_MODE = os.environ.get('DEPLOY_MODE', 'local')
AZURE_KEY_VAULT_URL = os.environ.get('AZURE_KEY_VAULT_URL')

# If AZURE_KEY_VAULT_URL is set, cloud mode is forced
if AZURE_KEY_VAULT_URL:
    DEPLOY_MODE = 'cloud'

# Unified reader:
secret = get_secret('GOOGLE_API_KEY')
# → local: reads from Vault KV v2
# → cloud: reads from Azure Key Vault (GOOGLE-API-KEY)
```

---

## CI/CD Pipeline

**File:** `.github/workflows/ci-cd.yml`

```
push to main
    │
    ▼
┌──────────┐     ┌────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  test    │────►│ build-and-push │────►│ update-manifests │────►│ security-scan│
│          │     │ (ACR)          │     │ (K8s repo)       │     │ (Trivy)      │
└──────────┘     └────────────────┘     └──────────────────┘     └──────────────┘
 Django tests     Multi-image build      sed image tags in        CVE scanning
 + frontend       backend + frontend     separate Git repo        SARIF upload
   lint+build     SHA-short tags         auto-commit + push
```

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `AZURE_CREDENTIALS` | Service principal JSON for ACR login |
| `ACR_USERNAME` | Azure Container Registry username |
| `ACR_PASSWORD` | Azure Container Registry password |
| `MANIFESTS_PAT` | PAT with repo write access to K8s manifests repo |

---

## GitOps (Argo CD)

### Installation

```bash
# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Install Argo CD Image Updater
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

# Apply VeriRAG application manifests
kubectl apply -f gitops/argocd/application.yaml
kubectl apply -f gitops/argocd/image-updater.yaml
```

### Auto-Deploy Flow

```
ACR new tag pushed
       │
       ▼
Image Updater (polls every 2m)
       │ detects new tag
       ▼
Commits new tag to K8s manifests repo
       │
       ▼
Argo CD (watches manifests repo)
       │ auto-sync
       ▼
Rolling update in cluster
```

---

## Local Mode — Quick Start

### Prerequisites

- Docker Desktop / Podman
- Kind or Minikube
- Helm 3
- `kubectl`

### Steps

```bash
# 1. Create cluster
kind create cluster --name verirag

# 2. Copy .env.example to .env and fill in values
cp .env.example .env

# 3. Install with Helm (local mode)
helm install verirag ./helm/verirag \
  --namespace verirag --create-namespace \
  --set secrets.postgresPassword=your-local-pg-pass \
  --set secrets.djangoSecretKey=$(python -c "import secrets; print(secrets.token_urlsafe(50))") \
  --set secrets.vaultToken=dev-root-token

# 4. Seed Vault with API keys
kubectl exec -n verirag deploy/verirag-vault -- vault kv put secret/myapp \
  GOOGLE_API_KEY=your-key-here \
  GROQ_API_KEY=your-groq-key-here

# 5. Access the app
kubectl port-forward -n verirag svc/verirag-frontend 3000:8080
# Open http://localhost:3000
```

---

## Cloud Mode — Azure Deployment

### Prerequisites

- Azure CLI (`az login`)
- Terraform >= 1.5
- Helm 3
- External Secrets Operator

### Step 1 — Provision Infrastructure

```bash
cd infrastructure

# Create terraform.tfvars from the example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

This creates:
- Resource Group
- Azure Container Registry (ACR)
- PostgreSQL Flexible Server (pgvector)  
- Azure Cache for Redis
- Azure Key Vault
- Azure Container Apps Environment + Backend + Celery Worker

### Step 2 — Seed Azure Key Vault

```bash
# Store API keys (the ONLY way they reach the application)
az keyvault secret set --vault-name kv-verirag-dev --name GOOGLE-API-KEY --value "your-key"
az keyvault secret set --vault-name kv-verirag-dev --name GROQ-API-KEY --value "your-key"
az keyvault secret set --vault-name kv-verirag-dev --name DJANGO-SECRET-KEY --value "$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
az keyvault secret set --vault-name kv-verirag-dev --name POSTGRES-USER --value "admin"
az keyvault secret set --vault-name kv-verirag-dev --name POSTGRES-PASSWORD --value "your-pg-password"
az keyvault secret set --vault-name kv-verirag-dev --name REDIS-CONNECTION-STRING --value "rediss://:access-key@host:6380/0"
```

### Step 3 — Deploy to AKS / ACA

**Option A — Azure Container Apps (Terraform-managed, already done):**
The `terraform apply` in Step 1 deploys the backend and Celery worker to ACA with KEDA scaling.

**Option B — AKS with Helm (for Kubernetes-native deployment):**

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system --create-namespace

# Deploy VeriRAG  
helm install verirag ./helm/verirag \
  --namespace verirag --create-namespace \
  -f helm/verirag/values.yaml \
  -f helm/verirag/values-production.yaml
```

---

## Burst Mode — AKS On-Demand

For massive AI workloads that exceed ACA limits. Spin up an AKS cluster, run the job, tear it down.

### Provision

```bash
cd infrastructure

terraform apply -target=module.aks_burst \
  -var="pg_admin_password=your-pg-pass" \
  -var="django_secret_key=your-django-key"

# Get credentials
az aks get-credentials --resource-group rg-verirag-dev --name aks-verirag-burst
```

### Deploy

```bash
helm install verirag ./helm/verirag \
  --namespace verirag --create-namespace \
  -f helm/verirag/values.yaml \
  -f helm/verirag/values-production.yaml
```

### Teardown (cost control)

```bash
terraform destroy -target=module.aks_burst
```

---

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n verirag
kubectl describe pod <pod-name> -n verirag
kubectl logs <pod-name> -n verirag
```

### Verify secrets are synced (ESO)
```bash
kubectl get externalsecret -n verirag
kubectl get secret verirag-secrets -n verirag -o jsonpath='{.data}' | jq
```

### Test Vault connectivity (local mode)
```bash
kubectl exec -n verirag deploy/verirag-vault -- vault status
kubectl exec -n verirag deploy/verirag-vault -- vault kv get secret/myapp
```

### Django health check
```bash
kubectl exec -n verirag deploy/verirag-backend -- curl -s http://localhost:8000/health/
```

### Force Argo CD sync
```bash
argocd app sync verirag
```

---

## File Reference

| File | Purpose |
|------|---------|
| `helm/verirag/values.yaml` | Local mode defaults |
| `helm/verirag/values-production.yaml` | Cloud mode overrides |
| `helm/verirag/templates/external-secret.yaml` | Azure Key Vault → K8s Secret sync |
| `infrastructure/main.tf` | Azure resources (PG, Redis, ACA, Key Vault) |
| `infrastructure/modules/aks-burst/main.tf` | On-demand AKS cluster |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline |
| `gitops/argocd/application.yaml` | Argo CD auto-sync config |
| `gitops/argocd/image-updater.yaml` | Auto-promote image tags |
| `backend/rag_backend/settings.py` | Dual-mode secret detection |
| `backend/ai_engine/rag_logic.py` | Dual-mode API key retrieval |
