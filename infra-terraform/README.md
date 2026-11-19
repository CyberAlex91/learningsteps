<!-- Zweck: Beschreibt Terraform-Betrieb, Architekturentscheidungen und Infrastruktur-Nachweise. -->
# LearningSteps Evolution – Terraform

## GitHub delivery identity prepared (not applied)

Update: user confirmed apply completed and full plan No changes. Public CI
client ID dc149d37-fe90-4f21-b23e-a56adc899e0f. Workflow delivery implementation
is prepared but has not yet demonstrated an authenticated push/deploy.

github-actions.tf prepares five resources after the first green CI run.
Own UAMI with exact immutable GitHub repository+feature-branch federation,
AcrPush only at ACR, custom read/runcommand/commandResults role assigned only
at LearningSteps AKS. This ARM deployment path preserves API IP restrictions.
Run Command is also subject to caller Kubernetes authorization in this cluster.
The first attempt was rejected until namespace deployment rights are added.
No state/direct Key Vault access, subscription Contributor or persistent
client secret is granted. Deploy workflow must wait for all security/quality
gates and accept trusted pushes only. Before merging delivery into main, review
the federation branch subject. fmt/validate/review plan first; expected five
additions with no existing-resource change/deletion. Client ID output is public.

First delivery passed OIDC/ACR but Kubernetes denied deployment get for the CI
identity; API stayed at its old healthy image. github-actions.tf now prepares a
second custom role with deployments/read and deployments/write DataActions,
assigned only to learningsteps namespace. Expected repair plan: two additions,
zero changes/deletions. Await review/apply and role propagation before rerun.

Update: namespace role/assignment applied (2 added), Terraform No changes.
Entra-oid SubjectAccessReview allowed patch. Failed delivery job rerun succeeded;
public API description now shows the new commit's code. Run44519207174 attempt2,
artifact downloaded outside Git. ARM invoke alone was insufficient; namespace
DataActions are required and now evidenced. Commit this source repair next.

## Public HTTPS address created (2026-11-19)

User applied the reviewed plan; IP exists and subsequent plan No changes.
Confirmed output: learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com.
Gateway/certificate still pending. Public IP incurs charges while retained.

public-access.tf defines one static Standard zone-redundant IP and Azure DNS
label in the existing AKS node resource group. AKS already manages networking
there; no additional role grant or resource-group ownership is introduced.
Expected plan: one addition, no changes/deletions. Public IP is billable while
it exists, including when AKS is stopped. No HTTPS service/certificate is created
by this Terraform file. A later gateway LoadBalancer must reference this IP by
name and node resource group. Remove the Kubernetes LoadBalancer service before
final infrastructure destruction; retain the remote-state bootstrap.

## Dynamic developer IP preparation

From LearningSteps in the VS Code WSL terminal, run
`python3 app/scripts/refresh_developer_access.py` for a read-only IP comparison.
With `--prepare`, it verifies the active subscription/tenant, detects and
validates a public IPv4, adds only that /32 to the vault firewall to permit
Terraform refresh, preserves other local tfvars and saves developer-ip.tfplan.
Review the full plan before applying; expected changes are only AKS/KV IP rules.
This is an on-demand update, not a background service or static ISP address.
The helper never applies, starts services or reads secret values. If planning
fails after the bootstrap, the added /32 remains until a successful reviewed
apply; no rollback/removal of other rules is attempted. A network/VPN change
may require another run. Keep the same network during prepare/apply.
After apply, check Terraform No changes and kubectl access. No extra Azure
resources are created by this helper.

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

### PostgreSQL server created; final plan verified

User applied database.tfplan: 4 added, 0 changed, 0 destroyed. The managed server
was created in about 6m54s, then the empty database and two TLS settings succeeded.
Azure selected zone 3 automatically; zone="3" was added to adopt this choice.
A subsequent full Terraform plan reported No changes. No SQL connection,
schema initialization or restricted app SQL role has been tested yet.
Database compute/storage charges now apply. Last confirmed code push before
this database step: d2c9dbf; server configuration/docs still to commit.
For an overnight pause, stop PostgreSQL and AKS through their service-specific
CLI commands, verify both stopped states, and start both before continuing.
Never delete data or run terraform destroy merely to pause overnight.

The following paragraph records the original prepared configuration.

User confirmed infrastructure/credentials committed and pushed as d2c9dbf.
database.tf now prepares PostgreSQL 15, B1ms, Premium_LRS P4 32 GiB,
seven-day local backup, no geo backup or HA standby, no storage autogrow.
This is a small learning environment, not a production HA configuration.
The server is private in West Europe and uses the previously created network.
Public server access is disabled. Explicit configurations require secure
transport and at least TLS 1.2. The existing vault admin password is read
ephemerally and passed into administrator_password_wo. No secret output.
The empty learningsteps database is created; schema/app SQL role are later steps.
Expected plan: 4 additions, 0 changes, 0 destructions. Apply will add roughly
EUR 17/month compute/storage list cost if kept running for 730 hours, plus
other services/backup over allowance. Do not apply without plan review.
prevent_destroy guards the server; preserve notes/backups and review the guard
explicitly before the final recovery exercise. AKS stop was proposed but has
not been executed; user chose to continue working for now.

### PostgreSQL private network complete; Key Vault prepared

Key Vault step subsequently applied by the user: 2 additions, 1 subnet change,
0 destructions; full plan No changes. Vault is now provisioned. Credential
configuration in database-credentials.tf is prepared but not applied yet:
two ephemeral random passwords, Key Vault write-only values, version trigger 1,
expiry 2027-02-16. No passwords in outputs, tfvars or regular secret data sources.
Run init for the new hashicorp/random ~>3.7 provider, then fmt/validate/plan.
Expected credential plan: 2 secret additions, 0 changes, 0 destructions.
The new lockfile selection must be committed. Do not enable Terraform debug
logging or display secret values. Database creation must read the persisted
vault credential ephemerally to remain consistent after partial apply retries.
Coordinated SQL/Key Vault credential rotation before expiry is a remaining task.

Update: user applied database-credentials.tfplan successfully (2 added,
0 changed, 0 destroyed). Both postgres-admin-password and postgres-app-password
exist in Key Vault; following plan No changes. Random provider 3.9.1 installed
and locked. No PostgreSQL server, SQL schema or app SQL role has been created
by this step. Next: create the server using an ephemeral read of the persisted
admin password into administrator_password_wo, then initialize schema and
restricted API role and configure pod secret access. Local notes stay unchanged.

Teaching preference reaffirmed by user: before each execution explain the goal,
why the component is needed, exact execution location, command meaning,
expected output, effects/costs and relation to the overall application. A clean
Terraform plan means configured infrastructure matches Azure, not that the
application is deployed or the entire project complete.

Germany West Central capability response restricted PostgreSQL provisioning.
West Europe, North Europe and Sweden Central offered server editions; West
Europe B1ms was selected. User applied database-network.tfplan: 10 added,
0 changed, 0 destroyed; subsequent plan No changes. data VNet 10.62.0.0/16,
subnet 10.62.1.0/24, NSG, two peerings, DNS zone and two links are provisioned.
The original Germany database subnet remains unused. No PostgreSQL server
or actual private database connection has been verified yet.

PostgreSQL name psql-learningsteps-alex-0ad5f630 is available. Original proposed
Key Vault name was too long; kv-lsteps-0ad5f630 is confirmed available.
`key-vault.tf` prepares a Standard vault in Germany with Entra RBAC, default-deny
firewall, the developer public /32 and the AKS subnet allowed. This requires
adding a Microsoft.KeyVault service endpoint to the existing AKS subnet.
User gets Secrets Officer at vault scope; app read-only permission comes later.
Plan expectation: 2 additions, 1 subnet change, 0 destructions. No secrets or
database server are created in this vault step. Key Vault operations are billable.
Soft delete is 7 days and purge protection enabled; provider skips permanent
purge on destroy and can recover the soft-deleted vault during rebuild.
Protection cannot be switched off after enabling; preserve recovery behavior
and data before the final destroy/rebuild exercise. CI requires its own network
allowance and secret permissions, not yet configured.

Next credentials step: ephemeral Key Vault reads and write-only PostgreSQL
password arguments, avoiding secret values in Terraform state/plan. Persist
credentials in Key Vault before database creation, so retries reuse the same
credential rather than generating mismatched values. Implementation pending.

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
# API workload identity preparation (2026-11-18)

User applied application-identity.tf: four resources added, zero changed/deleted;
subsequent full plan confirmed No changes on 2026-11-18. Resources: a dedicated
API user-assigned identity, federation for exactly
system:serviceaccount:learningsteps:learningsteps-api, a write-only Key Vault
postgres-app-database-url secret and Key Vault Secrets User scoped to that single
secret. The admin password remains outside the runtime identity's permissions.
The URL is derived ephemerally from the persisted app password and requires
PostgreSQL certificate and hostname verification. No credential outputs exist.
This does not deploy pods, enable Foundry or prove runtime secret access yet.
Next: mount the
secret with CSI, add DATABASE_URL_FILE support and verify denied admin access.
Credential rotation must coordinate the SQL role, password secret and derived
URL version; this step does not implement automatic SQL password rotation.
