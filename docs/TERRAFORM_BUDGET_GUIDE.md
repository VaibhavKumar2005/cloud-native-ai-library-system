# VeriRAG Terraform: $97 Budget-Optimized Deployment

> **Production-grade RAG system on Azure Container Apps, keeping costs under $97/month**

---

## 📊 Budget Allocation

| Service | Tier | Monthly Cost | Purpose |
|---------|------|--------------|---------|
| **Container Apps** | Consumption | ~$18 | Backend + Frontend (KEDA: scale-to-zero) |
| **PostgreSQL Flexible** | B1s | ~$28 | pgvector embeddings storage |
| **Redis Cache** | Basic | ~$22 | LLM response caching, session state |
| **Container Registry** | Basic | ~$5 | Docker image hosting |
| **Application Insights** | Pay-per-GB | ~$0.99 | Logs + metrics (1GB free tier) |
| **Key Vault** | Standard | ~$0.99 | Secret management |
| **Overages/Margin** | — | ~$10 | Buffer for unexpected costs |
| **TOTAL** | — | **~$85** | **15% under budget ✅** |

---

## 🔑 Key Terraform Decisions

### 1. **Container Apps (NOT Kubernetes)**

```hcl
resource "azurerm_container_app" "backend" {
  name                         = "ca-verirag-backend"
  container_app_environment_id = azurerm_container_app_environment.env.id
  
  template {
    container {
      name   = "backend"
      image  = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      cpu    = 0.25      # ← Minimum viable (1 = 1 vCPU)
      memory = "0.5Gi"   # ← Minimum viable
    }

    scale {
      min_replicas = 0        # ← CRITICAL: Scales to zero when idle
      max_replicas = 2        # ← Handle spike traffic
    }
  }
}
```

**Why NOT AKS?**
- AKS cluster = $73+/month (BLOCKER for $97 budget)
- Container Apps Consumption = $0.00 when idle, then $18-25 under load
- KEDA automatically scales pods to zero after 5 min inactivity
- No cluster management overhead

### 2. **PostgreSQL Flexible Server (B1s Only)**

```hcl
resource "azurerm_postgresql_flexible_server" "db" {
  name                   = "db-verirag"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = var.location
  administrator_login    = var.pg_admin_user
  administrator_password = random_password.pg_password.result

  sku_name   = "B_B1s"      # ← Burstable tier (dev/test)
  storage_mb = 32768        # ← 32GB (pgvector doesn't need massive storage)
  
  backup_retention_days = 7  # ← Minimal retention
  
  # ← CRITICAL: Disable unused features to save costs
  geo_redundancy_enabled = false
  high_availability_enabled = false
}
```

**Why B1s NOT General Purpose?**
- B1s = $28/month
- General Purpose = $150+/month (10x more expensive!)
- B1s handles: 100GB embeddings, 1000+ daily queries
- Scale up to General Purpose only when you need HA

### 3. **Redis Basic (Strict Configuration)**

```hcl
resource "azurerm_redis_cache" "cache" {
  name                = "redis-verirag"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  capacity            = 0           # ← Basic tier (250MB)
  family              = "C"         # ← Consumer (not Enterprise)
  sku_name            = "Basic"     # ← NOT Standard or Premium
  
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  
  # ← Skip clustering, replication, zones (ALL cost money)
}
```

**Cache Usage Strategy:**
- Store: LLM responses (TTL: 3600s), embeddings cache (TTL: 86400s)
- 250MB = ~50,000 cached responses @ 5KB each
- Use aggressive TTLs: `CACHE_TTL = 3600` seconds

### 4. **Container Registry: Minimal Configuration**

```hcl
resource "azurerm_container_registry" "acr" {
  name                = "acr${replace(var.project_name, "-", "")}2026"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location

  sku                = "Basic"      # ← NOT Standard or Premium
  admin_enabled      = false        # ← Use managed identity instead
  
  # ← SKIP: Geo-replication, network rules, zones
}
```

**Image Retention Strategy:**
```bash
# Delete untagged images after 30 days to save storage
az acr task create \
  --registry $ACR_NAME \
  --name cleanup \
  --cmd "acr purge \
    --filter 'verirag-backend:\\!latest' \
    --ago 30d" \
  --schedule "0 0 * * *"  # Daily at midnight UTC
```

---

## 🚀 Deployment Commands

### Initialize & Plan

```bash
cd ops/infrastructure

# Set variables
export TF_VAR_location="centralindia"
export TF_VAR_pg_admin_password="YourStrongPassword123!"
export TF_VAR_django_secret_key="your-django-secret-key"
export TF_VAR_acr_name="acrverirag2026"

# Initialize Terraform
terraform init

# Plan deployment (preview changes)
terraform plan -out=tfplan
```

### Deploy to Azure

```bash
# Apply the plan
terraform apply tfplan

# Outputs will include:
# - Container Registry URL
# - PostgreSQL connection string
# - Redis connection string
# - Container Apps URLs
terraform output
```

### Save Outputs

```bash
terraform output -json > ../outputs.json

# Extract key values for .env
export POSTGRES_HOST=$(terraform output -raw postgres_host)
export REDIS_HOST=$(terraform output -raw redis_host)
export ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
```

---

## 💰 Cost Optimization Checklist

### Before Deploying
- [ ] PostgreSQL: sku_name = `B_B1s` (baseline for $97 budget)
- [ ] Redis: sku_name = `Basic` (250MB, no clustering)
- [ ] Container Registry: sku = `Basic`
- [ ] Container Apps: `min_replicas = 0` (scale to zero)
- [ ] Disable backup redundancy: `geo_redundancy_enabled = false`
- [ ] Set cache TTLs to aggressive values (Redis storage saving)

### After Deploying
- [ ] Monitor: `terraform output monthly_cost_estimate` (should be ~$85)
- [ ] Set Azure Budgets alert at $90/month
- [ ] Review monthly Container Apps execution time (should be <100 hrs)
- [ ] Check Redis memory usage (should be <50% capacity)
- [ ] Archive image tags older than 30 days

---

## 🛠️ Common Scaling Scenarios

### Scenario 1: "I'm hitting Redis capacity"
**Problem:** Cache is full (250MB limit)
**Solution:** Increase Redis capacity
```hcl
capacity = 1  # Upgrade to 1GB ($60/mo - still in budget)
```
**Cost impact:** +$32/month (new total: ~$117)

### Scenario 2: "PostgreSQL is slow"
**Problem:** B1s is only 1vCPU, 2GB RAM
**Solution:** Migrate to General Purpose
```hcl
sku_name = "GP_Standard_B2s"  # 2vCPU, 16GB RAM
```
**Cost impact:** +$120/month (new total: ~$205) ❌ OUT OF BUDGET

**Better solution:** Optimize queries first
- Add indexes on `embedding` columns
- Increase `CACHE_TTL` to reduce DB queries
- Use connection pooling (PgBouncer)

### Scenario 3: "I need high availability"
**Problem:** Single PostgreSQL instance = risk
**Solution:** Enable standby replica
```hcl
high_availability_enabled = true
```
**Cost impact:** +$28/month (new total: ~$113)

---

## 📈 Monitoring Your $97 Budget

### Azure Budgets Alert (Portal)
```
Subscriptions → Budgets → Create
Amount: $97
Alert at: 90% ($87.30)
Recipients: your-email@example.com
```

### Cost Analysis Dashboard
```bash
az costmanagement query create \
  --name "VeriRAG Monthly" \
  --definition '{
    "type": "Usage",
    "timeframe": "MonthToDate",
    "dataset": {
      "granularity": "Daily",
      "aggregation": {
        "totalCost": {"name": "PostTaxCost", "function": "Sum"}
      },
      "filter": {
        "dimensions": {
          "name": "ResourceGroup",
          "operator": "In",
          "values": ["rg-verirag-dev"]
        }
      }
    }
  }'
```

### Real-time Cost Tracking (Your CostOps System)
```python
# From your existing ops system - use it!
from ai_engine.costops import get_cost_tracker

tracker = get_cost_tracker()
current_spend = tracker.get_monthly_total()
budget_remaining = 97 - current_spend

print(f"Budget utilization: {(current_spend/97)*100:.1f}%")
print(f"Remaining: ${budget_remaining:.2f}")
```

---

## 🔄 Updating the Infrastructure

### Add a Feature (Staying Within Budget)
```hcl
# Example: Add Azure Cognitive Search for hybrid search
resource "azurerm_search_service" "search" {
  name                = "search-verirag"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  sku                 = "basic"  # $75/month - BREAKS BUDGET ❌
}

# DECISION: Skip this until budget increases
```

### Scale Down (Emergency Cost Cutting)
```hcl
# If month is looking expensive:
# 1. Reduce PostgreSQL from B1s to B1ms (micro)
sku_name = "B_B1ms"  # Save $10/month

# 2. Reduce Container Apps max_replicas
max_replicas = 1  # Handle less concurrent load

# 3. Increase cache TTLs (reduce database hits)
CACHE_TTL = 7200  # 2 hours instead of 1 hour
```

---

## 🚨 What NOT to Do on $97 Budget

| ❌ DON'T | Why | Alternative |
|---------|-----|-------------|
| Deploy to **AKS** | $73+ per cluster | ✅ Container Apps Consumption |
| Use **Geo Redundancy** | +$30/month | ✅ Daily backups (retention: 7d) |
| Enable **High Availability** | +$28/month | ✅ Single zone (add HA later) |
| **Premium Redis** | $600+/month | ✅ Basic Cache + aggressive TTLs |
| **General Purpose Postgres** | $150+/month | ✅ B1s Burstable (scale up later) |
| **Multiple regions** | x2-3 cost | ✅ Single region (scale later) |
| Azure **Application Gateway** | $16+/month | ✅ Built-in Container Apps routing |
| **Log Analytics workspace** | $31+/month | ✅ Use Application Insights basic |

---

## 📋 Production Checklist

Before marking as production-ready:

- [ ] **Network Security**
  - [ ] PostgreSQL: Public access disabled, private endpoint enabled
  - [ ] Redis: SSL/TLS enabled, firewall configured
  - [ ] ACR: Anonymous pull disabled, RBAC roles assigned

- [ ] **Secrets Management**
  - [ ] All API keys in Key Vault (not in `.env`)
  - [ ] Managed Identity configured for Container Apps
  - [ ] No secrets in Terraform state (use `sensitive = true`)

- [ ] **Monitoring**
  - [ ] Application Insights connected
  - [ ] Azure Monitor alerts configured
  - [ ] Cost anomaly detection enabled
  - [ ] CostOps system verified to track spend

- [ ] **Data Protection**
  - [ ] PostgreSQL backup: 7+ days retention
  - [ ] Redis persistence: Enabled (RDB snapshots)
  - [ ] Images in ACR: Signed & scanned for vulnerabilities

- [ ] **Scaling Ready**
  - [ ] Container Apps: min_replicas = 0, max_replicas = 2
  - [ ] KEDA configured (scale trigger: CPU 70%, Memory 75%)
  - [ ] Connection pooling: Enabled for PostgreSQL

---

## 🆘 Troubleshooting

### "Terraform apply failed: quota exceeded"
```bash
# Check current quotas
az vm list-usage --location centralindia

# Request quota increase via Portal
# Compute → Vmss Cores → Request quota increase
```

### "Container Apps failing to pull image"
```bash
# Verify ACR credentials
az acr credential show --name $ACR_NAME

# Check managed identity permissions
az role assignment list --assignee-object-id <MI_OBJECT_ID>

# Assign AcrPull role
az role assignment create \
  --assignee-object-id <MI_OBJECT_ID> \
  --role AcrPull \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME
```

### "PostgreSQL connection timeout"
```bash
# Check firewall rules
az postgres flexible-server firewall-rule list --resource-group rg-verirag-dev

# Add Container Apps outbound IP
OUTBOUND_IP=$(az container app show -n ca-verirag-backend -g rg-verirag-dev --query properties.outboundIpAddresses -o tsv)

az postgres flexible-server firewall-rule create \
  --name AllowContainerApps \
  --resource-group rg-verirag-dev \
  --server-name db-verirag \
  --start-ip-address $OUTBOUND_IP \
  --end-ip-address $OUTBOUND_IP
```

---

## 📚 Next Steps

1. **Month 1:** Run on this setup, track actual costs
2. **Month 2:** If costs are stable at <$85, you've won! 🎉
3. **Month 3+:** Based on usage patterns, decide scaling:
   - More users? → Increase Container Apps max_replicas
   - More queries? → Upgrade Redis to Standard tier
   - Need HA? → Enable PostgreSQL high availability

---

**Last Updated:** April 6, 2026  
**Terraform Version:** 1.5+  
**Azure Provider:** 3.85+
