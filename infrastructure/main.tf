###############################################################################
# VeriRAG — Infrastructure as Code (Terraform)
#
# Provisions the CLOUD MODE infrastructure on Azure:
#   1. Resource Group
#   2. Azure Container Registry (ACR)
#   3. Azure Database for PostgreSQL Flexible Server (pgvector)
#   4. Azure Cache for Redis (Basic Tier)
#   5. Azure Container Apps Environment + Apps (KEDA scale-to-zero)
#   6. Azure Key Vault (cloud-mode secret management)
#   7. Log Analytics Workspace (observability)
#
# Burst Mode (AKS) is in a separate module: modules/aks-burst/
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
  }

  # Uncomment for remote state (recommended for teams)
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "stveriragstate"
  #   container_name       = "tfstate"
  #   key                  = "verirag.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "centralindia"
}

variable "project_name" {
  description = "Project prefix used in all resource names"
  type        = string
  default     = "verirag"
}

variable "environment" {
  description = "Environment tag (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "pg_admin_user" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "veriragadmin"
  sensitive   = true
}

variable "pg_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "acr_name" {
  description = "Globally unique ACR name"
  type        = string
  default     = "acrvaibhavrag2026"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    project     = "VeriRAG"
    environment = var.environment
    managed_by  = "terraform"
    team        = "team96"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. RESOURCE GROUP
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.common_tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONTAINER REGISTRY (ACR)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.common_tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. LOG ANALYTICS WORKSPACE (for ACA + monitoring)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. AZURE DATABASE FOR POSTGRESQL — FLEXIBLE SERVER (pgvector)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_postgresql_flexible_server" "pg" {
  name                          = "pg-${local.resource_prefix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  version                       = "16"
  administrator_login           = var.pg_admin_user
  administrator_password        = var.pg_admin_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms" # Burstable for dev; upgrade in prod
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true # Set false + VNet in prod

  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "verirag_db" {
  name      = "verirag_db"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Enable pgvector extension
resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.pg.id
  value     = "VECTOR"
}

# Allow Azure services to connect
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. AZURE CACHE FOR REDIS (Basic Tier — cost-effective for dev)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_redis_cache" "redis" {
  name                = "redis-${local.resource_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  non_ssl_port_enabled = true # Required for Celery; use SSL in prod
  minimum_tls_version  = "1.2"
  tags                 = local.common_tags
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6. AZURE KEY VAULT (Cloud-mode secret management)
# ═══════════════════════════════════════════════════════════════════════════════

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                       = "kv-${local.resource_prefix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false # Set true in prod

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge"
    ]
  }

  tags = local.common_tags
}

# Store DB connection string in Key Vault
resource "azurerm_key_vault_secret" "pg_connection" {
  name         = "POSTGRES-CONNECTION-STRING"
  value        = "postgresql://${var.pg_admin_user}:${var.pg_admin_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/verirag_db?sslmode=require"
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "redis_connection" {
  name         = "REDIS-CONNECTION-STRING"
  value        = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
  key_vault_id = azurerm_key_vault.kv.id
}

# ═══════════════════════════════════════════════════════════════════════════════
# 7. AZURE CONTAINER APPS ENVIRONMENT (Scale-to-Zero)
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_container_app_environment" "aca_env" {
  name                       = "cae-${local.resource_prefix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  tags                       = local.common_tags
}

# ── 7a. Backend API (Container App) ────────────────────────────────────────
resource "azurerm_container_app" "backend" {
  name                         = "ca-${local.resource_prefix}-backend"
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  template {
    min_replicas = 0 # Scale to zero!
    max_replicas = 5

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "rag_backend.settings"
      }
      env {
        name  = "DEPLOY_MODE"
        value = "cloud"
      }
      env {
        name  = "DEBUG"
        value = "False"
      }
      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.pg.fqdn
      }
      env {
        name  = "POSTGRES_DB"
        value = "verirag_db"
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
        name  = "REDIS_URL"
        value = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
      }
      env {
        name  = "AZURE_KEY_VAULT_URL"
        value = azurerm_key_vault.kv.vault_uri
      }
    }

    # KEDA HTTP scaler — scale to 0 when no traffic
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

# ── 7b. Celery Worker (Container App with KEDA Redis Scaler) ──────────────
resource "azurerm_container_app" "celery_worker" {
  name                         = "ca-${local.resource_prefix}-worker"
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  template {
    min_replicas = 0 # Scale to zero when queue is empty!
    max_replicas = 3

    container {
      name   = "celery-worker"
      image  = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      command = [
        "celery", "-A", "rag_backend", "worker",
        "-l", "info",
        "-Q", "celery,ingestion,monitoring,maintenance",
        "--concurrency=2"
      ]

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "rag_backend.settings"
      }
      env {
        name  = "DEPLOY_MODE"
        value = "cloud"
      }
      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.pg.fqdn
      }
      env {
        name  = "POSTGRES_DB"
        value = "verirag_db"
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
        name  = "REDIS_URL"
        value = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
      }
      env {
        name  = "CELERY_BROKER_URL"
        value = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}/0"
      }
      env {
        name  = "AZURE_KEY_VAULT_URL"
        value = azurerm_key_vault.kv.vault_uri
      }
    }

    # KEDA: Scale based on Redis queue length
    custom_scale_rule {
      name             = "redis-queue-scaler"
      custom_rule_type = "redis"
      metadata = {
        host          = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:${azurerm_redis_cache.redis.ssl_port}"
        listName      = "celery"
        listLength    = "5"
        enableTLS     = "true"
      }
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
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.acr.admin_username
}

output "acr_password" {
  value     = azurerm_container_registry.acr.admin_password
  sensitive = true
}

output "postgresql_fqdn" {
  value = azurerm_postgresql_flexible_server.pg.fqdn
}

output "redis_hostname" {
  value = azurerm_redis_cache.redis.hostname
}

output "redis_primary_key" {
  value     = azurerm_redis_cache.redis.primary_access_key
  sensitive = true
}

output "key_vault_uri" {
  value = azurerm_key_vault.kv.vault_uri
}

output "backend_app_url" {
  value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "aca_environment_id" {
  value = azurerm_container_app_environment.aca_env.id
}