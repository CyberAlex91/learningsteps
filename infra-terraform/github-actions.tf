# Verified from GitHub's repository OIDC customization API (immutable subjects).
# Only this trusted push branch is accepted; PR subjects and forks do not match.
resource "azurerm_user_assigned_identity" "github_actions" {
  name                = "id-learningsteps-github-actions"
  resource_group_name = azurerm_resource_group.evolution.name
  location            = azurerm_resource_group.evolution.location
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_federated_identity_credential" "github_actions" {
  name                      = "github-trusted-feature-branch"
  user_assigned_identity_id = azurerm_user_assigned_identity.github_actions.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:CyberAlex91@287638010/learningsteps@1425944756:ref:refs/heads/feature/user-notes-summary"
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                            = azurerm_container_registry.evolution.id
  role_definition_name             = "AcrPush"
  principal_id                     = azurerm_user_assigned_identity.github_actions.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

# ARM Run Command avoids opening the Kubernetes API to changing public runners.
# It is effectively cluster-admin execution INSIDE this one cluster, not a
# namespace-limited Kubernetes deploy role. No subscription/RG Contributor grant.
resource "azurerm_role_definition" "github_aks_command" {
  name        = "LearningSteps CI AKS Run Command"
  scope       = azurerm_resource_group.evolution.id
  description = "Read and invoke Run Command on the assigned LearningSteps AKS cluster."

  permissions {
    actions = [
      "Microsoft.ContainerService/managedClusters/read",
      "Microsoft.ContainerService/managedClusters/runcommand/action",
      "Microsoft.ContainerService/managedClusters/commandResults/read",
    ]
  }

  assignable_scopes = [azurerm_resource_group.evolution.id]
}

resource "azurerm_role_assignment" "github_aks_command" {
  scope                            = azurerm_kubernetes_cluster.evolution.id
  role_definition_id               = azurerm_role_definition.github_aks_command.role_definition_resource_id
  principal_id                     = azurerm_user_assigned_identity.github_actions.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

output "github_actions_client_id" {
  description = "Public CI identity client ID; no client secret is created."
  value       = azurerm_user_assigned_identity.github_actions.client_id
}
