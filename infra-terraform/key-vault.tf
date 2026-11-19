# Zweck: Erstellt Key Vault mit rollenbasiertem Zugriff und Netzbeschränkungen.
resource "azurerm_key_vault" "evolution" {
  name                          = "kv-lsteps-0ad5f630"
  resource_group_name           = azurerm_resource_group.evolution.name
  location                      = azurerm_resource_group.evolution.location
  tenant_id                     = "c0531484-50fa-4ff2-97df-b1f2d4810603"
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  soft_delete_retention_days    = 7
  purge_protection_enabled      = true
  public_network_access_enabled = true
  tags                          = local.evolution_tags

  # HTTPS endpoint is network-restricted; Entra authorization is also required.
  network_acls {
    default_action             = "Deny"
    bypass                     = "None"
    ip_rules                   = [var.aks_api_allowed_cidr]
    virtual_network_subnet_ids = [azurerm_subnet.aks.id]
  }

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

# Subscription Owner alone does not grant Key Vault secret data access.
resource "azurerm_role_assignment" "vault_operator" {
  scope                = azurerm_key_vault.evolution.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.aks_admin_object_id
  principal_type       = "User"
}

# Application identity will receive read-only access to its specific secret later.
# No passwords or secret values are provisioned by this initial vault step.
