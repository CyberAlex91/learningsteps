# Zweck: Erstellt die Azure Container Registry ohne aktiviertes Administratorkonto.
resource "azurerm_container_registry" "evolution" {
  name                          = "acrlearningstepsalex0ad5f630"
  resource_group_name           = azurerm_resource_group.evolution.name
  location                      = azurerm_resource_group.evolution.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  role_assignment_mode          = "LegacyRegistryPermissions"
  tags                          = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}
