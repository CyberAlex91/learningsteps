locals {
  evolution_tags = {
    project = "LearningSteps"
    stage   = "Evolution"
  }
}

resource "azurerm_resource_group" "evolution" {
  name     = "rg-learningsteps-evolution"
  location = "germanywestcentral"

  tags = local.evolution_tags

  # Azure added this metadata during creation. Keep it externally managed.
  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_virtual_network" "evolution" {
  name                = "vnet-learningsteps-evolution"
  location            = azurerm_resource_group.evolution.location
  resource_group_name = azurerm_resource_group.evolution.name
  address_space       = ["10.60.0.0/16"]
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_subnet" "aks" {
  name                            = "snet-aks"
  resource_group_name             = azurerm_resource_group.evolution.name
  virtual_network_name            = azurerm_virtual_network.evolution.name
  address_prefixes                = ["10.60.0.0/22"]
  default_outbound_access_enabled = false

  service_endpoint {
    service = "Microsoft.KeyVault"
  }
}

resource "azurerm_subnet" "database" {
  name                            = "snet-postgres"
  resource_group_name             = azurerm_resource_group.evolution.name
  virtual_network_name            = azurerm_virtual_network.evolution.name
  address_prefixes                = ["10.60.4.0/24"]
  default_outbound_access_enabled = false

  delegation {
    name = "postgres-flexible-server"

    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }

  # Flexible Server uses Azure Storage for managed operations.
  service_endpoint {
    service = "Microsoft.Storage"
  }
}
