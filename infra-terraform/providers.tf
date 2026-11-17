provider "azurerm" {
  features {}

  subscription_id                 = "0ad5f630-c506-401a-93fa-36b0fe313829"
  tenant_id                       = "c0531484-50fa-4ff2-97df-b1f2d4810603"
  storage_use_azuread             = true
  resource_provider_registrations = "none"
}
