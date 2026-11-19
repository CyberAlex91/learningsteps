# Zweck: Erstellt AKS mit Entra-Zugriff, Netzwerk, Workload Identity und Container-Registry-Rechten.
resource "azurerm_user_assigned_identity" "aks_control_plane" {
  name                = "id-learningsteps-aks-control"
  resource_group_name = azurerm_resource_group.evolution.name
  location            = azurerm_resource_group.evolution.location
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_role_assignment" "aks_subnet" {
  scope                            = azurerm_subnet.aks.id
  role_definition_name             = "Network Contributor"
  principal_id                     = azurerm_user_assigned_identity.aks_control_plane.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_kubernetes_cluster" "evolution" {
  name                              = "aks-learningsteps-evolution"
  location                          = azurerm_resource_group.evolution.location
  resource_group_name               = azurerm_resource_group.evolution.name
  node_resource_group               = "rg-learningsteps-evolution-nodes"
  dns_prefix                        = "learningsteps-alex"
  kubernetes_version                = "1.36.5"
  sku_tier                          = "Free"
  role_based_access_control_enabled = true
  local_account_disabled            = true
  oidc_issuer_enabled               = true
  workload_identity_enabled         = true
  node_os_upgrade_channel           = "NodeImage"
  tags                              = local.evolution_tags

  node_provisioning_profile {
    mode               = "Manual"
    default_node_pools = "None"
  }

  default_node_pool {
    name                        = "system"
    node_count                  = 2
    vm_size                     = "Standard_D4s_v6"
    zones                       = ["2", "3"]
    vnet_subnet_id              = azurerm_subnet.aks.id
    max_pods                    = 30
    os_sku                      = "AzureLinux3"
    os_disk_type                = "Managed"
    os_disk_size_gb             = 64
    temporary_name_for_rotation = "systemtmp"

    upgrade_settings {
      max_surge                     = "1"
      drain_timeout_in_minutes      = 30
      node_soak_duration_in_minutes = 0
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_control_plane.id]
  }

  azure_active_directory_role_based_access_control {
    tenant_id          = "c0531484-50fa-4ff2-97df-b1f2d4810603"
    azure_rbac_enabled = true
  }

  api_server_access_profile {
    authorized_ip_ranges = [var.aks_api_allowed_cidr]
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    network_policy      = "cilium"
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = "10.61.0.0/16"
    dns_service_ip      = "10.61.0.10"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer"

    load_balancer_profile {
      managed_outbound_ip_count = 1
    }
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }

  depends_on = [azurerm_role_assignment.aks_subnet]
}

resource "azurerm_role_assignment" "aks_pull" {
  scope                            = azurerm_container_registry.evolution.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.evolution.kubelet_identity[0].object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "aks_admin" {
  scope                = azurerm_kubernetes_cluster.evolution.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = var.aks_admin_object_id
  principal_type       = "User"
}
