# LearningSteps Evolution – acceptance checklist

Status: 2026-11-19. Approximate progress 75%; implementation estimates are not
a course grade. The daily AI exercise is submitted according to the user.

## Authenticated public acceptance (2026-11-19)

HTTPS Swagger SPA callback added to LearningSteps-Alex-Swagger, with existing
localhost callback preserved. User completed browser authorization and created
then listed a real own cloud note through the public HTTPS API. Entry ID:
199c9471-746e-4c13-90f4-1f9dec1ac1c0, created at2026-11-19T11:18:02.814455+00:00.
GET entries returned that note and count1. Preserve it as acceptance evidence;
do not delete/overwrite it during subsequent tests. This proves authenticated
create/read through gateway, API and private DB. Cloud PATCH/DELETE and cloud AI
are not yet evidenced. Own-note isolation tests were performed separately earlier.

No GitHub Actions workflow exists yet. Next milestone: lint/tests/build,
secret/image/IaC gates, then OIDC-authorized push/deploy. Public HTTPS success
does not establish continuous delivery, scaling or full recovery acceptance.

## Done and evidenced

- [x] Local Docker build, non-root runtime and hardened startup smoke test.
- [x] HIGH/CRITICAL vulnerability gate: rejected Bookworm and Trixie candidates;
  accepted patched Alpine application image without suppressions (Trivy exit 0).
- [x] ACR Basic provisioned by Terraform, admin disabled, Entra login.
- [x] Accepted image pushed; digest matches the tested build.
- [x] Entra-based Terraform remote state with versioning and soft delete.
- [x] VNet with separate AKS and delegated PostgreSQL subnets provisioned.
- [x] Existing Foundry account adopted into Terraform; model remains removed.

## Remaining required weekly work

Database step completed after credential/network commit d2c9dbf:
4 added, 0 changed, 0 destroyed. PostgreSQL 15 B1ms server, empty learningsteps
database, TLS enforcement and TLS minimum were created. Azure chose zone 3;
the configuration now explicitly adopts zone 3, and the subsequent plan No changes
is confirmed. AKS-to-database private DNS, TCP and verified TLSv1.3 passed.
Uses the persisted Key Vault admin password through an ephemeral read and
administrator_password_wo, with the secret rotation version as trigger.
Schema and restricted learningsteps_app role were subsequently configured and
tested: row count unchanged at 0, actual app login/SELECT over TLSv1.3, DML
permissions verified and CREATE TABLE rejected. Both diagnostic pods removed.
Evidence is saved outside Git under ../artifacts/azure. Explicit prevent_destroy
guard must be reviewed after backup before the final recovery demonstration.

### PostgreSQL regional availability blocker (2026-11-18)

CLI list-skus for germanywestcentral returned success but no server editions or
versions. Saved artifact: ../artifacts/azure/postgres-skus-germanywestcentral.json.
The response reason explicitly says provisioning is restricted in this region
and recommends a support request for exceptions; OfferRestricted is Enabled.
This does not establish lack of PostgreSQL support in Germany for all customers.
Alternative capability responses for West Europe, North Europe and Sweden
Central list editions/versions without the regional restriction. West Europe
B1ms was chosen. User applied database-network.tfplan: 10 added, 0 changed,
0 destroyed; subsequent full plan No changes. Data VNet 10.62.0.0/16,
delegated subnet 10.62.1.0/24, NSG, both peerings and private DNS links to both
VNets are created. The server was subsequently provisioned and connectivity
verified as described above. The Germany AKS cluster remains in place.

User's public retail price readback: B1ms EUR 0.0179/hour and Flexible Server
Storage EUR 0.1229/GB-month, giving approximately EUR 17/month for 730 compute
hours and 32 storage units. Excludes DNS, peering/transfer, backup beyond the
included allowance and other Azure services. Next: server and Key Vault names,
then secure credential provisioning and database Terraform configuration.

- [x] AKS cluster created by Terraform; subsequent plan No changes.
- [x] Developer Entra/Azure CLI access verified; two Kubernetes 1.36.5 nodes Ready,
  Azure Linux 3.0, private IPs only. Separate WSL kubeconfig used.
- [ ] Configure restricted CI access.
- [x] PostgreSQL Flexible Server and private DNS created, seven-day backup configured.
- [x] Verify private DB connection/TLS, initialize schema and restricted SQL app role;
  preserve existing local notes.
- [ ] Demonstrate cloud database backup/restore.
- [x] Key Vault integration into Kubernetes diagnostic pod with narrow identity permissions.
  Preparation applied: API user-assigned identity, exact service-account
  federation, write-only database URL secret and secret-scoped read role.
  Apply 4 added, 0 changed, 0 destroyed; subsequent plan No changes. Actual CSI
  mount, app-role SELECT over verified TLSv1.3 and explicit ForbiddenByRbac for
  admin secret passed on 2026-11-19. Evidence workload-access-check.json; pod
  removed. Non-root file access uses 0444 after 0440 group mismatch was diagnosed.
  Reusable SA/SPC retained. The API deployment still needs to consume this mount.
- [x] Key Vault created with firewall/RBAC and two separate password secrets;
  credential apply: 2 added, 0 changed, 0 destroyed; subsequent plan No changes.
  Password values use ephemeral generation and write-only storage arguments.
  The restricted SQL role now exists and its login was verified. Runtime pod
  access through Workload Identity remains pending.
- [x] Kubernetes API Deployment, internal Service and ConfigMap rolled out;
  user confirmed two 1/1 Running pods, no restarts. Runtime image digest matches
  tested and scanned image bca3adb76034cf55982987c43988247a93f58e03303b208d4c9b636f9ce10d7f.
- [x] Public HTTPS gateway with required LoadBalancer Service.
  Traefik scan passed, AMD64 digest verified in publisher index and ACR. Gateway
  Ready, 4Gi certificate PVC Bound, public IP131.189.29.152. User confirmed public
  CA/hostname verification, docs/readiness200, entries401 and HTTP redirect.
  Evidence https-access-check.json. Entra HTTPS callback and interactive login
  still pending. First-start certificate race must be automated for recovery.
- [x] Readiness/liveness probes and resource requests/limits deployed.
  Runtime code now supports DATABASE_URL_FILE and /health/live, /health/ready.
  User ran all nine offline runtime configuration/probe tests: OK (2026-11-19).
  Production-image build, smoke test, scan, ACR push and deployment passed.
- [ ] Horizontal Pod Autoscaler, load demonstration and replica recovery.
- [ ] GitHub Actions on pushes: lint, tests and Docker build.
- [ ] Secret scan, image vulnerability scan, Terraform static security analysis.
- [ ] HIGH/CRITICAL findings fail pipeline; intentional negative test proves this.
- [ ] Federated GitHub OIDC authentication and narrowly scoped Azure permissions.
- [ ] Successful scans followed by ACR push and automatic AKS deployment.
- [ ] Demonstrate a pushed code change becoming live automatically.
- [ ] Preserve evidence, then final Terraform destroy/apply recovery test.
- [ ] Technical report, screenshots, runnable instructions and course submission.

## AI extension to preserve through migration

- [x] Actual stored own notes summarized, with authenticated user separation.
- [ ] Replace local Azure CLI credential with AKS Workload Identity.
- [ ] Model deployment and application RBAC expressed in Terraform.
- [ ] Verify stored-note summary on Azure-hosted application without key exposure.

## Optional scope

- [ ] Prometheus instrumentation, Prometheus/Grafana and dashboard for request
  count, latency and database health. Optional in brief; not implicitly complete.

## AKS sizing preflight

User confirmed Kubernetes 1.36.5 available and Compute/ContainerService/
ManagedIdentity registered. Standard_D4s_v6 lists zone 1 restriction; zones 2/3
have no listed restriction (not a capacity guarantee). Latest Compute readback:
regional vCPU quota 30, Dsv6 family quota 20, both usage 0. Two 4-vCPU nodes
plus one update-surge node fit. Regular Linux retail VM price returned by
scripts/check_aks_vm_price.py: EUR 0.2172/node-hour, EUR 0.4344/two-node-hour,
EUR 10.43/two-node-day, EUR 317.11/730 hours. These are compute-only list prices,
not total cost or a spend cap. Additional disks/network/services are billable.
AKS apply succeeded: 5 added, 0 changed, 0 destroyed; subsequent plan No changes.
kubectl access and two Ready nodes verified by user output. Running costs apply.
