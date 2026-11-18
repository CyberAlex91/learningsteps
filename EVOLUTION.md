# LearningSteps Evolution – acceptance checklist

Status: 2026-11-18. Approximate progress 50%; implementation estimates are not
a course grade. The daily AI exercise is submitted according to the user.

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

- [x] AKS cluster created by Terraform; subsequent plan No changes.
- [x] Developer Entra/Azure CLI access verified; two Kubernetes 1.36.5 nodes Ready,
  Azure Linux 3.0, private IPs only. Separate WSL kubeconfig used.
- [ ] Configure restricted CI access.
- [ ] PostgreSQL Flexible Server, private DNS, schema/migration and backup plan.
- [ ] Key Vault integration into Kubernetes pods with narrow identity permissions.
- [ ] Kubernetes Deployment, LoadBalancer Service and ConfigMap.
- [ ] Readiness/liveness probes and resource requests/limits.
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
