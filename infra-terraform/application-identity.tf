# This is the API workload identity, separate from AKS control-plane and kubelet
# identities. Only the named Kubernetes service account can federate with it.
resource "azurerm_user_assigned_identity" "api" {
  name                = "id-learningsteps-api"
  resource_group_name = azurerm_resource_group.evolution.name
  location            = azurerm_resource_group.evolution.location
  tags                = local.evolution_tags

  lifecycle {
    ignore_changes = [tags["created-on"]]
  }
}

resource "azurerm_federated_identity_credential" "api" {
  name                      = "learningsteps-api-service-account"
  user_assigned_identity_id = azurerm_user_assigned_identity.api.id
  issuer                    = azurerm_kubernetes_cluster.evolution.oidc_issuer_url
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "system:serviceaccount:learningsteps:learningsteps-api"
}

# Read the persisted app password, not a newly generated random value. This read
# and the derived write-only URL never persist the credential in plans/state.
ephemeral "azurerm_key_vault_secret" "postgres_app" {
  name         = azurerm_key_vault_secret.postgres_password["app"].name
  key_vault_id = azurerm_key_vault.evolution.id
  version      = azurerm_key_vault_secret.postgres_password["app"].version

  depends_on = [azurerm_role_assignment.vault_operator]
}

resource "azurerm_key_vault_secret" "api_database_url" {
  name         = "postgres-app-database-url"
  key_vault_id = azurerm_key_vault.evolution.id
  value_wo = format(
    "postgresql://learningsteps_app:%s@%s:5432/learningsteps?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt",
    urlencode(ephemeral.azurerm_key_vault_secret.postgres_app.value),
    azurerm_postgresql_flexible_server.evolution.fqdn,
  )
  value_wo_version = azurerm_key_vault_secret.postgres_password["app"].value_wo_version
  content_type     = "text/plain"
  expiration_date  = "2027-02-16T00:00:00Z"
  tags = {
    project = "LearningSteps"
    purpose = "api-database-connection"
  }

  depends_on = [azurerm_role_assignment.vault_operator]
}

# Secret-specific scope deliberately separates runtime access from the admin
# credential in this shared project vault. No list/write or admin-secret grant.
resource "azurerm_role_assignment" "api_database_secret" {
  scope                            = "${azurerm_key_vault.evolution.id}/secrets/${azurerm_key_vault_secret.api_database_url.name}"
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
