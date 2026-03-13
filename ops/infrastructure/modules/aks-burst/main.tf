###############################################################################
# VeriRAG — AKS Burst Mode Module
#
# Provisions a full Azure Kubernetes Service cluster ONLY when massive
# scaling is required. Designed to be applied independently and destroyed
# when burst capacity is no longer needed.
#
# Usage:
#   cd infrastructure/modules/aks-burst
#   terraform init
#   terraform apply -var="pg_admin_password=..." -var="redis_primary_key=..."
#
# Teardown (stop costs):
#   terraform destroy
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
  features {}
}

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

variable "location" {
  description = "Azure region"
  type        = string
  default     = "centralindia"
}

variable "resource_group_name" {
  description = "Existing resource group (from main infra)"
  type        = string
  default     = "rg-verirag-dev"
}

variable "acr_id" {
  description = "Resource ID of the ACR to attach"
  type        = string
}

variable "pg_fqdn" {
  description = "PostgreSQL Flexible Server FQDN"
  type        = string
}

variable "pg_admin_user" {
  type      = string
  sensitive = true
}

variable "pg_admin_password" {
  type      = string
  sensitive = true
}

variable "redis_hostname" {
  type = string
}

variable "redis_primary_key" {
  type      = string
  sensitive = true
}

variable "redis_ssl_port" {
  type    = number
  default = 6380
}

variable "key_vault_uri" {
  description = "Azure Key Vault URI for secret management"
  type        = string
}

variable "node_count" {
  description = "Initial node count for system pool"
  type        = number
  default     = 2
}

variable "vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D4s_v5"
}

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

locals {
  cluster_name = "aks-verirag-burst"
  common_tags = {
    project     = "VeriRAG"
    environment = "burst"
    managed_by  = "terraform"
    purpose     = "high-scale-burst"
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# AKS CLUSTER
# ═══════════════════════════════════════════════════════════════════════════════

resource "azurerm_kubernetes_cluster" "aks" {
  name                = local.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "verirag-burst"
  kubernetes_version  = var.k8s_version
  tags                = local.common_tags

  default_node_pool {
    name            = "system"
    vm_size         = var.vm_size
    os_disk_size_gb = 128
    max_pods        = 50
    min_count       = 1
    max_count       = 5

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for AKS monitoring"
  type        = string
}

# ── GPU/Worker Node Pool (for heavy AI workloads) ──────────────────────────
resource "azurerm_kubernetes_cluster_node_pool" "workers" {
  name                  = "workers"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D8s_v5"
  os_disk_size_gb       = 128
  min_count             = 0    # Scale to zero when not needed
  max_count             = 10
  mode                  = "User"

  node_labels = {
    "workload" = "ai-processing"
  }

  node_taints = [
    "workload=ai-processing:NoSchedule"
  ]

  tags = local.common_tags
}

# ── Attach ACR to AKS (no imagePullSecrets needed) ────────────────────────
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}

output "cluster_fqdn" {
  value = azurerm_kubernetes_cluster.aks.fqdn
}

output "kubelet_identity_object_id" {
  value = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# ── Kubeconfig helper ─────────────────────────────────────────────────────
output "get_credentials_command" {
  value = "az aks get-credentials --resource-group ${var.resource_group_name} --name ${local.cluster_name} --overwrite-existing"
}
