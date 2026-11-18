# Germany West Central PostgreSQL provisioning is restricted for this subscription.
# Keep AKS in place; use private cross-region networking to West Europe.
resource "azurerm_resource_group" "data" {
  name     = "rg-learningsteps-data"
  location = "westeurope"
  tags     = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_virtual_network" "data" {
  name                = "vnet-learningsteps-data"
  resource_group_name = azurerm_resource_group.data.name
  location            = azurerm_resource_group.data.location
  address_space       = ["10.62.0.0/16"]
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_subnet" "postgres_westeurope" {
  name                            = "snet-postgres"
  resource_group_name             = azurerm_resource_group.data.name
  virtual_network_name            = azurerm_virtual_network.data.name
  address_prefixes                = ["10.62.1.0/24"]
  default_outbound_access_enabled = false

  delegation {
    name = "postgres-flexible-server"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }

  service_endpoint {
    service = "Microsoft.Storage"
  }
}

resource "azurerm_network_security_group" "postgres" {
  name                = "nsg-learningsteps-postgres"
  resource_group_name = azurerm_resource_group.data.name
  location            = azurerm_resource_group.data.location
  tags                = local.evolution_tags

  security_rule {
    name                       = "AllowPostgresFromAKS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.60.0.0/22"
    destination_address_prefix = "10.62.1.0/24"
  }

  # Preserve service-required communication inside the delegated subnet.
  security_rule {
    name                       = "AllowPostgresWithinSubnet"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.62.1.0/24"
    destination_address_prefix = "10.62.1.0/24"
  }

  security_rule {
    name                       = "DenyOtherInbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Outbound defaults retained for managed-service operations (Storage/Entra/DNS).
  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_subnet_network_security_group_association" "postgres" {
  subnet_id                 = azurerm_subnet.postgres_westeurope.id
  network_security_group_id = azurerm_network_security_group.postgres.id
}

resource "azurerm_virtual_network_peering" "aks_to_data" {
  name                         = "aks-to-data"
  resource_group_name          = azurerm_resource_group.evolution.name
  virtual_network_name         = azurerm_virtual_network.evolution.name
  remote_virtual_network_id    = azurerm_virtual_network.data.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = false
  allow_gateway_transit        = false
  use_remote_gateways          = false
}

resource "azurerm_virtual_network_peering" "data_to_aks" {
  name                         = "data-to-aks"
  resource_group_name          = azurerm_resource_group.data.name
  virtual_network_name         = azurerm_virtual_network.data.name
  remote_virtual_network_id    = azurerm_virtual_network.evolution.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = false
  allow_gateway_transit        = false
  use_remote_gateways          = false
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "learningsteps.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.data.name
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres_data" {
  name                 = "postgres-to-data-vnet"
  private_dns_zone_id  = azurerm_private_dns_zone.postgres.id
  virtual_network_id   = azurerm_virtual_network.data.id
  registration_enabled = false
  tags                 = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres_aks" {
  name                 = "postgres-to-aks-vnet"
  private_dns_zone_id  = azurerm_private_dns_zone.postgres.id
  virtual_network_id   = azurerm_virtual_network.evolution.id
  registration_enabled = false
  tags                 = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres_data]
}
