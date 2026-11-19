# Zweck: Vergibt OIDC-Föderation und begrenzte Azure-/Kubernetes-Auslieferungsrechte an GitHub Actions.
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
  subject                   = "repo:CyberAlex91@287638010/learningsteps@1425944756:ref:refs/heads/main"
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                            = azurerm_container_registry.evolution.id
  role_definition_name             = "AcrPush"
  principal_id                     = azurerm_user_assigned_identity.github_actions.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

# ARM Run Command avoids opening the Kubernetes API to changing public runners.
# Entra/Azure RBAC also authorizes the caller INSIDE this cluster; the ARM
# permission alone does not grant deployment access. No RG Contributor grant.
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

# Only deployment get/watch/update is needed for set image, rollout status and
# image readback. No direct secret read, pod exec, role binding or delete grant.
resource "azurerm_role_definition" "github_namespace_deploy" {
  name        = "LearningSteps CI Namespace Deployment"
  scope       = azurerm_resource_group.evolution.id
  description = "Read and update Kubernetes deployments in the assigned namespace."

  permissions {
    data_actions = [
      "Microsoft.ContainerService/managedClusters/apps/deployments/read",
      "Microsoft.ContainerService/managedClusters/apps/deployments/write",
    ]
  }

  assignable_scopes = [azurerm_resource_group.evolution.id]
}

resource "azurerm_role_assignment" "github_namespace_deploy" {
  scope                            = "${azurerm_kubernetes_cluster.evolution.id}/namespaces/learningsteps"
  role_definition_id               = azurerm_role_definition.github_namespace_deploy.role_definition_resource_id
  principal_id                     = azurerm_user_assigned_identity.github_actions.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

output "github_actions_client_id" {
  description = "Public CI identity client ID; no client secret is created."
  value       = azurerm_user_assigned_identity.github_actions.client_id
}
