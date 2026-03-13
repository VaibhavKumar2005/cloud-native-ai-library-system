###############################################################################
# VeriRAG — Infrastructure as Code (Terraform)
#
# Provisions the CLOUD MODE infrastructure on Azure:
#   1. Resource Group
#   2. Azure Container Registry (ACR)
#   3. Azure Database for PostgreSQL Flexible Server (pgvector)
#   4. Azure Cache for Redis (Basic Tier - Secure SSL)
#   5. Azure Container Apps Environment + Apps (KEDA scale-to-zero)
#   6. Azure Key Vault (cloud-mode secret management)
###############################################################################

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES & LOCALS
# ═══════════════════════════════════════════════════════════════════════════════

variable "location" { default = "centralindia" }
variable "project_name" { default = "verirag" }
variable "environment" { default = "dev" }
variable "pg_admin_user" {
  default   = "veriragadmin"
  sensitive = true
}
variable "pg_admin_password" { sensitive = true }
variable "django_secret_key" { sensitive = true }
variable "acr_name" { default = "acrvaibhavrag2026" }

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    project     = "VeriRAG"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CORE RESOURCES (RG, ACR, LOGS)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATABASE (PostgreSQL Flexible + pgvector)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "pg-${local.resource_prefix}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "16"
  administrator_login    = var.pg_admin_user
  administrator_password = var.pg_admin_password
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms"
  tags                   = local.common_tags
}

resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.pg.id
  value     = "VECTOR" # [cite: 82]
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. REDIS (Secure SSL Configuration)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_redis_cache" "redis" {
  name                 = "redis-${local.resource_prefix}"
  location             = azurerm_resource_group.rg.location
  resource_group_name  = azurerm_resource_group.rg.name
  capacity             = 0
  family               = "C"
  sku_name             = "Basic"
  non_ssl_port_enabled = false # FIX 
  minimum_tls_version  = "1.2"
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONTAINER APPS ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_container_app_environment" "aca_env" {
  name                       = "cae-${local.resource_prefix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

# ── 4a. Backend API ──────────────────────────────────────────────────────────
resource "azurerm_container_app" "backend" {
  name                         = "ca-${local.resource_prefix}-backend"
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  template {
    min_replicas = 0 # Scale-to-zero cost optimization 
    max_replicas = 3
    container {
      name   = "backend"
      image  = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      cpu    = 0.5
      memory = "1Gi"
      env {
        name  = "DEPLOY_MODE"
        value = "cloud"
      }
      env {
        name  = "ALLOWED_HOSTS"
        value = "*"
      }
      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.pg.fqdn
      }
      env {
        name        = "POSTGRES_USER"
        secret_name = "pg-user"
      }
      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "pg-password"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
    }
    http_scale_rule {
      name                = "http-scaler"
      concurrent_requests = "10"
    }
  }

  secret {
    name  = "pg-user"
    value = var.pg_admin_user
  }
  secret {
    name  = "pg-password"
    value = var.pg_admin_password
  }
  secret {
    name  = "redis-url"
    value = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
  }
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ── 4b. Celery Worker ────────────────────────────────────────────────────────
resource "azurerm_container_app" "celery_worker" {
  name                         = "ca-${local.resource_prefix}-worker"
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  template {
    min_replicas = 0
    max_replicas = 2
    container {
      name    = "celery-worker"
      image   = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      cpu     = 0.5
      memory  = "1Gi"
      command = ["celery", "-A", "rag_backend", "worker", "-l", "info", "-Q", "celery,ingestion"]
      env {
        name  = "DEPLOY_MODE"
        value = "cloud"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
    }
  }

  secret {
    name  = "redis-url"
    value = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
  }
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }
}

# ── 4c. Frontend UI ──────────────────────────────────────────────────────────
resource "azurerm_container_app" "frontend" {
  name                         = "ca-${local.resource_prefix}-frontend"
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  template {
    min_replicas = 0
    max_replicas = 1
    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.acr.login_server}/verirag-frontend:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      # FIX: Pass the dynamic backend URL to the React app [cite: 58, 60]
      env {
        name  = "VITE_API_URL"
        value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
      }
    }
    http_scale_rule {
      name                = "http-scaler"
      concurrent_requests = "20"
    }
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  ingress {
    external_enabled = true
    target_port      = 8080 # Correct Nginx/Vite port 
    transport        = "auto"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

output "frontend_url" { value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}" }
output "backend_url"  { value = "https://${azurerm_container_app.backend.ingress[0].fqdn}" }
