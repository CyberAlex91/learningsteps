# Zweck: Konfiguriert AzureRM und die Erzeugung beziehungsweise Verwendung von Zufallswerten.
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }

  subscription_id                 = "0ad5f630-c506-401a-93fa-36b0fe313829"
  tenant_id                       = "c0531484-50fa-4ff2-97df-b1f2d4810603"
  storage_use_azuread             = true
  resource_provider_registrations = "none"
}
