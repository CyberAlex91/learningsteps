# Place the static IP in AKS's existing node resource group. The control-plane
# identity already manages networking there; no extra broad IAM grant is needed.
resource "azurerm_public_ip" "https" {
  name                = "pip-learningsteps-https"
  resource_group_name = azurerm_kubernetes_cluster.evolution.node_resource_group
  location            = azurerm_resource_group.evolution.location
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  domain_name_label   = "learningsteps-alex-0ad5f630"
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

output "application_hostname" {
  description = "Public hostname for the future HTTPS gateway; not yet a live URL."
  value       = azurerm_public_ip.https.fqdn
}
