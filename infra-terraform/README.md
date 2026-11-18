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

### AKS created and Terraform verified (2026-11-18)

User confirmed successful apply: 5 added, 0 changed, 0 destroyed. Cluster
creation completed in about 5m37s plus identity and role assignment setup.
All three explicit role assignments succeeded; subsequent full plan reported
No changes. Remote state acquisition/release was visible. User then connected
using Azure CLI authentication and kubelogin v0.2.22, with a separate WSL file
`~/.kube/learningsteps-evolution.yaml`. Both Kubernetes 1.36.5 nodes report Ready,
Azure Linux 3.0 and only private node IPs. Application deployment remains pending.
Running node, disk and networking charges now apply.

For a fresh WSL terminal, restore the session settings before kubectl commands:

```bash
export PATH="$PATH:$HOME/.local/share/learningsteps-tools/bin"
export KUBECONFIG="$HOME/.kube/learningsteps-evolution.yaml"
```

Do not copy kubeconfig or CLI authentication caches into the repository.

`aks.tf` adds five Terraform resources: a control-plane managed identity,
Network Contributor restricted to the AKS subnet, the cluster, kubelet AcrPull
restricted to this registry, and human Azure RBAC Cluster Admin restricted to
this cluster. Azure-managed dependent resources also incur charges even though
they are not separate entries in the Terraform plan.

Cluster candidate: Kubernetes 1.36.5, Free control-plane tier, two D4s_v6
nodes in zones 2/3, 64-GiB managed OS disks, one surge node for updates.
Compute-only public list price: EUR 0.4344/hour or EUR 10.43/24h for both
nodes. Disks, load balancer, outbound public IP, transfer and other services
are additional; an update-surge node temporarily adds compute cost.
Latest user readback: regional quota 30, Dsv6 family 20, both usage 0.

AzureLinux3 nodes use Azure CNI Overlay/Cilium. Explicit outbound connectivity
uses a standard load balancer and managed public IP; implicit subnet outbound
remains disabled. Pod CIDR 10.244.0.0/16, service CIDR 10.61.0.0/16.
Entra/Azure RBAC enabled, local accounts disabled. Kubernetes API access limited
to a developer IPv4 /32. OIDC/Workload Identity and Key Vault CSI driver are
enabled; actual application federation/secret access will be configured later.
For this learning cluster the single system pool also hosts the application;
this is not full production isolation between system and application workloads.

Run `python3 app/scripts/prepare_aks_local.py` from LearningSteps in WSL first.
It reads the signed-in user's object ID and public IPv4 via api.ipify.org,
then writes ignored local auto-tfvars (no secrets). It refuses to overwrite
existing inputs. Confirm the source IP is suitable when VPN/proxy is involved;
refresh the allowlist deliberately after public IP changes. CI later needs
its own OIDC permissions and an API network access strategy; not yet implemented.
Do not replace the human admin ID automatically with a future CI identity.
Next: fmt, validate and saved plan, then review before any creation.

### Container Registry deployed and verified (2026-11-18)

The user applied the reviewed plan: 1 added, 0 changed, 0 destroyed.
The subsequent full plan reported No changes. Registry creation is complete
and recurring Basic charges now apply. The user subsequently pushed
`learningsteps-api:evolution-cc8174d` to this registry; the returned manifest
digest matched the scanned Alpine image. See SECURITY-SCANS.md for acceptance.
Interactive push used the existing inherited Owner role and an Entra-based
Docker login. No additional role or registry admin credentials were needed.
Dedicated narrow CI/AKS permissions remain to be configured.

User confirmed no infrastructure drift, registry name
`acrlearningstepsalex0ad5f630` available, and Microsoft.ContainerRegistry
Registered. `registry.tf` adds one Basic registry with admin credentials disabled.
Public network connectivity is enabled; image access requires authentication.
Basic does not provide the Premium private-endpoint/firewall features. The
explicit LegacyRegistryPermissions mode supports later AcrPull/AcrPush roles;
actual application and CI role assignments are not configured yet.
Shared static tags avoid the previously encountered resource-derived tag issue.
Only the externally added created-on tag is ignored for updates.

The reviewed plan had 1 addition, 0 changes, 0 destructions. Registry creation incurs
recurring Basic tier charges even when no containers run and no images exist;
storage above the included amount and applicable transfer can add costs.
No image build, upload, login or AKS provisioning is included in this step.

### Networking: deployed and verified

The corrected saved plan was applied successfully according to user output:
3 added, 0 changed, 0 destroyed (VNet and both subnets). The resource group had
already been created by the first attempt. A subsequent full plan reported
`No changes. Your infrastructure matches the configuration.`
The network foundation is complete; workload isolation and managed services
are still pending. The following paragraph records the resolved first attempt.

The first validated plan contained 4 additions. During apply the resource group
was successfully created. Azure added a `created-on` tag, which changed the
resource-derived tag map passed to the VNet and triggered `Provider produced
inconsistent final plan`. The output does not confirm VNet or subnet creation.
The exact actor adding the tag (for example an Azure Policy) is not verified.

Correction: both resources use the same static `local.evolution_tags` map,
not computed tags from another resource. Only the externally added `created-on`
tag is ignored for updates on these two resources; project/stage tags remain
managed. The old saved plan was not reused. Formatting and validation passed,
and the replacement plan contained 3 additions, 0 changes, 0 destructions.

`network.tf` defines four additions: resource group `rg-learningsteps-evolution`,
VNet `vnet-learningsteps-evolution` (10.60.0.0/16), AKS subnet `snet-aks`
(10.60.0.0/22), and PostgreSQL subnet `snet-postgres` (10.60.4.0/24).
The user confirmed no existing VNets in the subscription and Microsoft.Network
Registered. Local/VPN/peered address space overlap has not been independently
checked; recheck before any future network connection.

The database subnet delegates to Microsoft.DBforPostgreSQL/flexibleServers and
has a Microsoft.Storage service endpoint. Implicit outbound access is disabled
on both subnets. AKS will need explicit outbound connectivity as part of its
cluster configuration. No NAT gateway or public IP is created in this step.
Subnets alone do not restrict traffic between workloads: NSG rules, Kubernetes
network policies and database access controls remain later tasks. There is no
AKS cluster or database server yet. Private DNS will be added with PostgreSQL.

Foundry must remain unchanged in the next plan.

The Terraform foundation was pushed in commit `918ced7`. Save the new network
configuration and updated documentation in Git next. Local caches, saved plans
and state files must remain ignored. Next infrastructure component: ACR, after
checking resource provider registration and the chosen registry name.
The model deployment learningsteps-summary was deleted after the exercise;
do not recreate it until its Terraform configuration and intended use are ready.
Add networking, ACR, AKS, PostgreSQL Flexible Server, Key Vault and identity in
subsequent reviewed steps. Never put Azure CLI caches or tokens in the image.
