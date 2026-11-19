# INTENTIONALLY INSECURE NEGATIVE CI TEST. Never merge or terraform apply.
resource "azurerm_network_security_group" "negative_ci_only" {
  name                = "DO-NOT-DEPLOY-negative-ci"
  location            = "germanywestcentral"
  resource_group_name = "DO-NOT-DEPLOY-NEGATIVE-CI"

  security_rule {
    name                       = "INTENTIONAL-OPEN-SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "0.0.0.0/0"
    destination_address_prefix = "*"
  }
}
