# Zweck: Verwaltet die übernommene Foundry-Ressourcengruppe und das schlüssellos konfigurierte Konto.
# Match the existing resources before changing their configuration.
resource "azurerm_resource_group" "ai" {
  name     = "rg-learningsteps-ai"
  location = "germanywestcentral"

  tags = {
    created-on = "2026-11-17T14:38:39.8586633Z"
    exercise   = "DevSecOps15"
    project    = "LearningSteps"
  }

  # Temporary guard during adoption; revisit for the final recovery exercise.
  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_cognitive_account" "foundry" {
  name                          = "learningsteps-ai-alex-709d408c"
  location                      = azurerm_resource_group.ai.location
  resource_group_name           = azurerm_resource_group.ai.name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = "learningsteps-ai-alex-709d408c"
  project_management_enabled    = true
  local_auth_enabled            = false
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = {
    created-on = "2026-11-17T14:41:04.8380279Z"
    exercise   = "DevSecOps15"
    project    = "LearningSteps"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Standard inference deployment, not reserved/provisioned throughput.
resource "azurerm_cognitive_deployment" "summary" {
  count                = var.enable_ai_summary ? 1 : 0
  name                 = "learningsteps-summary"
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = "gpt-5-mini"
    version = "2025-08-07"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }

  version_upgrade_option = "NoAutoUpgrade"
}

# Inference only at this account; no management/key or subscription grant.
resource "azurerm_role_assignment" "api_foundry" {
  count                            = var.enable_ai_summary ? 1 : 0
  scope                            = azurerm_cognitive_account.foundry.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

# Existing developer RBAC remains separate and is adopted for reproducibility.
resource "azurerm_role_assignment" "developer_foundry" {
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.aks_admin_object_id
  principal_type       = "User"
}
