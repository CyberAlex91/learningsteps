terraform {
  backend "azurerm" {
    subscription_id      = "0ad5f630-c506-401a-93fa-36b0fe313829"
    tenant_id            = "c0531484-50fa-4ff2-97df-b1f2d4810603"
    resource_group_name  = "rg-learningsteps-tfstate"
    storage_account_name = "lsstatealex0ad5f630"
    container_name       = "tfstate"
    key                  = "evolution.terraform.tfstate"
    use_azuread_auth     = true
  }
}
