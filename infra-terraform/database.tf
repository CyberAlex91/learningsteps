# Zweck: Erstellt die private PostgreSQL-Instanz und Datenbank mit erzwungenem TLS.
# Read the already persisted credential. Never use a regular secret data source:
# its value would be written into state. Ephemeral reads and write-only password
# fields keep the value out of both saved plans and state.
ephemeral "azurerm_key_vault_secret" "postgres_admin" {
  name         = azurerm_key_vault_secret.postgres_password["admin"].name
  key_vault_id = azurerm_key_vault.evolution.id
  version      = azurerm_key_vault_secret.postgres_password["admin"].version

  depends_on = [azurerm_role_assignment.vault_operator]
}

resource "azurerm_postgresql_flexible_server" "evolution" {
  name                = "psql-learningsteps-alex-0ad5f630"
  resource_group_name = azurerm_resource_group.data.name
  location            = azurerm_resource_group.data.location
  # No fixed zone: let Azure select available capacity for the single lab server.
  version                           = "15"
  sku_name                          = "B_Standard_B1ms"
  storage_mb                        = 32768
  storage_type                      = "Premium_LRS"
  storage_tier                      = "P4"
  backup_retention_days             = 7
  geo_redundant_backup_enabled      = false
  auto_grow_enabled                 = false
  delegated_subnet_id               = azurerm_subnet.postgres_westeurope.id
  private_dns_zone_id               = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled     = false
  administrator_login               = "learningsteps_admin"
  administrator_password_wo         = ephemeral.azurerm_key_vault_secret.postgres_admin.value
  administrator_password_wo_version = azurerm_key_vault_secret.postgres_password["admin"].value_wo_version
  tags                              = local.evolution_tags

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = false
  }

  lifecycle {
    ignore_changes  = [tags["created-on"], zone]
    prevent_destroy = true
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.postgres_data,
    azurerm_private_dns_zone_virtual_network_link.postgres_aks,
    azurerm_subnet_network_security_group_association.postgres,
    azurerm_virtual_network_peering.aks_to_data,
    azurerm_virtual_network_peering.data_to_aks,
  ]
}

resource "azurerm_postgresql_flexible_server_database" "learningsteps" {
  name      = "learningsteps"
  server_id = azurerm_postgresql_flexible_server.evolution.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_configuration" "require_tls" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.evolution.id
  value     = "on"
}

resource "azurerm_postgresql_flexible_server_configuration" "minimum_tls" {
  name      = "ssl_min_protocol_version"
  server_id = azurerm_postgresql_flexible_server.evolution.id
  value     = "TLSv1.2"
}
