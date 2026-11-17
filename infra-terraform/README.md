# LearningSteps Evolution – Terraform

## Status 2026-11-17

Backend initialization and validation succeeded according to user CLI output.
AzureRM 5.14.0 was installed and recorded in `.terraform.lock.hcl`.
`foundry.tf` describes the existing resource group and Foundry account.
The user applied the reviewed import plan: 2 imported, 0 added, 0 changed,
0 destroyed. `state list` confirmed both addresses below and the following plan
reported `No changes`. Completed import blocks were removed after adoption;
resource configuration and remote state remain intact. This also avoids trying
to import nonexistent resources during a later fresh rebuild.

- `azurerm_resource_group.ai`: `/subscriptions/0ad5f630-c506-401a-93fa-36b0fe313829/resourceGroups/rg-learningsteps-ai`
- `azurerm_cognitive_account.foundry`: `/subscriptions/0ad5f630-c506-401a-93fa-36b0fe313829/resourceGroups/rg-learningsteps-ai/providers/Microsoft.CognitiveServices/accounts/learningsteps-ai-alex-709d408c`
Temporary `prevent_destroy` guards block resource deletion/replacement during
adoption. Review these explicitly before the final recovery exercise.
Public network access remains enabled to match the current Azure resource;
this does not permit anonymous inference. Local/key authentication stays off.
Run commands in the WSL terminal of VS Code from the LearningSteps directory:

```bash
terraform -chdir=app/infra-terraform fmt -check
terraform -chdir=app/infra-terraform init
terraform -chdir=app/infra-terraform validate
```

Initialization uses the signed-in WSL Azure CLI identity and Entra authorization
for Blob Storage, without storage keys. CI will later use federated OIDC login.
Commit `.terraform.lock.hcl` after initialization to record the selected provider
version and checksums. Never commit local state, saved plans or private variables.
Resource provider registrations are handled explicitly, not automatically.

## Backend bootstrap (confirmed by user CLI output)

- Subscription: Alexander Plank - Sub.
- Resource group: rg-learningsteps-tfstate, germanywestcentral.
- Storage account: lsstatealex0ad5f630, StorageV2, Standard_LRS.
- HTTPS required; minimum TLS 1.2; anonymous Blob access and shared-key access disabled.
- Private container: tfstate. Signed-in user: Storage Blob Data Contributor
  scoped to this storage account.
- Versioning enabled; Blob and container soft delete: 7 days.
- Prior versions have no automatic expiry configured yet and consume storage.
- Backend network restrictions/private endpoints are not configured yet.
- State key reserved for this environment: evolution.terraform.tfstate.

These bootstrap resources are deliberately outside the application state and
must survive the final application destroy/rebuild exercise. Keep their setup
documented separately; the storage remains billable while retained. The import
persisted the resource mapping through the configured remote backend. A deliberate
concurrent-lock test has not been performed.

## Next steps

Save configuration, documentation and provider lock file in Git. Verify that
local caches, saved plans and state files remain ignored.
The model deployment learningsteps-summary was deleted after the exercise;
do not recreate it until its Terraform configuration and intended use are ready.
Add networking, ACR, AKS, PostgreSQL Flexible Server, Key Vault and identity in
subsequent reviewed steps. Never put Azure CLI caches or tokens in the image.
