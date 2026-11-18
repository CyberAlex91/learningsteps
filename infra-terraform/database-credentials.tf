# Ephemeral values do not persist in Terraform state or saved plans.
ephemeral "random_password" "postgres" {
  for_each = toset(["admin", "app"])

  length      = 40
  special     = false
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
}

# Persist passwords in Key Vault BEFORE using them to initialize PostgreSQL.
# The database must read the saved value ephemerally, so retries use the same
# password rather than a newly generated value.
resource "azurerm_key_vault_secret" "postgres_password" {
  for_each = toset(["admin", "app"])

  name             = "postgres-${each.key}-password"
  key_vault_id     = azurerm_key_vault.evolution.id
  value_wo         = ephemeral.random_password.postgres[each.key].result
  value_wo_version = 1
  content_type     = "text/plain"
  expiration_date  = "2027-02-16T00:00:00Z"
  tags = {
    project = "LearningSteps"
    purpose = "postgres-${each.key}"
  }

  depends_on = [azurerm_role_assignment.vault_operator]
}

# No plaintext outputs, regular secret data sources or password tfvars files.
# Incrementing value_wo_version rotates the corresponding secret intentionally;
# coordinate SQL role changes first. Plan rotation before 2027-02-16; automated
# SQL credential rotation is not implemented by this configuration.
