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

# No model deployment: the AI function deliberately remains unavailable.
# Existing developer RBAC is not yet managed here. AKS Workload Identity and
# narrowly scoped application permissions will be added in a later step.
