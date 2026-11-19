# CI/CD preparation

## Delivery implementation prepared (not yet run)

User applied the five CI identity resources; subsequent Terraform plan No changes.
Public client ID dc149d37-fe90-4f21-b23e-a56adc899e0f. Configure GitHub repository
variables AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID (public IDs, not
client secrets). No GitHub variable values have been changed by this edit.

Workflow now has a separate delivery job with needs on all three successful
checks and trusted-push repo/branch conditions matching federation. Only that
job receives id-token:write. Scanned image TAR, SHA256 and image ID transfer via
same-run artifact (one-day retention); download integrity failure is fatal.
Verify archive and loaded image before Azure login; no rebuild occurs. Push with
git-SHA tag, verify ACR digest, deploy by digest. Deployment evidence retained14days.
Actions pinned to official commit IDs resolved via GitHub API on2026-11-19.

ci_deploy.py validates GitHub context and registry digest, invokes only API image
update/rollout/readback commands through ARM. Requires both Azure CLI success and
remote exitCode0 plus digest confirmation. No app logs, secrets or SQL readback.
Does not apply manifests or reset HPA replica count. Manifest is bootstrap;
subsequent API image changes are delivery-owned, recorded in workflow evidence.
Successful public HTTPS check follows deployment. First delivery remains unproven.
test_ci_delivery.py tests untrusted-context/tag rejection and remote failure
handling with mocked transport. No real Azure credentials involved.

api/main.py replaces obsolete localhost login guidance with Authorize/Entra
guidance as the visible code-change proof after first automatic deployment.
Workflow concurrency no longer cancels an in-flight delivery when a later push
arrives. Required follow-ups: real delivery run, negative gate demonstration,
history scan, main-branch migration and first-start HTTPS recovery automation.

## First GitHub run passed (2026-11-19)

Commit b1e4f17 successfully triggered run44515789181:
https://github.com/CyberAlex91/learningsteps/actions/runs/44515789181
All three jobs and their lint/tests/secret/IaC/build/smoke/vulnerability steps
completed successfully. Local updated IaC scan also passed without missing-input
warning. This proves CI checks; image upload and deployment are not automated yet.

GitHub CLI read confirmed use_immutable_subject=true and exact prefix
repo:CyberAlex91@287638010/learningsteps@1425944756. Prepared github-actions.tf
uses that prefix plus ref:refs/heads/feature/user-notes-summary. Five new resources
expected: UAMI, federation, scoped AcrPush, custom Run Command role, cluster-scoped
assignment. No client secret, state access or direct Key Vault role. Not applied.
Run Command effectively permits cluster-admin shell execution inside this one
cluster; it is NOT namespace isolation, even though ARM actions/scope are narrow.
Chosen lab tradeoff avoids a new runner VM or opening API firewall to runner IPs.
Deploy job must be a separate trusted-push job after ALL check jobs; PRs/forks get
no CI identity match. Reassess this model before multi-tenant production use.
Before moving delivery to main, update exact federation subject deliberately.

## Checks prepared, not run on GitHub yet

.github/workflows/ci.yml runs on push, pull_request and manual dispatch.
Three independent jobs: lint/unit/real-PostgreSQL isolation, source secret/IaC
security, production image build/startup/vulnerability scan. A failed job keeps
the workflow failed; HIGH/CRITICAL scans use exit-code1 with no ignore-unfixed
or policy exclusions. Terraform source gate is untested: existing configuration
may have findings that require remediation before delivery can be added.

Initial local Terraform scan passed HIGH/CRITICAL but warned about two unset
input variables. Both local helper and CI now generate explicit synthetic scan
inputs (UUID000...001, documentation address203.0.113.10/32), passed with --tf-vars.
This models one restricted /32 without reading the developer file. These values
are for static analysis only, never infrastructure deployment. Confirm the
updated scan succeeds without the missing-variable warning before first push.

Checks have only contents:read, checkout credentials are not persisted, no
id-token:write and no Azure secrets/Foundry tokens. PR code may execute only in
these unprivileged ephemeral runners. Do not use pull_request_target.
Actions use maintained v7 release tags; pin reviewed action commit SHAs before
final delivery/security acceptance. Ruff0.14.14 is a fixed tool dependency;
initial gate targets syntax/invalid constructs/undefined names, not style or
complete static code security analysis. PostgreSQL15 service is ephemeral and
contains synthetic ci-only credentials, not a production password.

scripts/ci_tests.py refuses non-GitHub, non-loopback or wrong-name/user database
targets. Runs three existing unittest suites in separate processes, initializes
the disposable base DB and executes the real two-user isolation test. Existing
local/cloud data cannot be selected through its permitted DSN. No Azure/model
calls are required. Production Dockerfile/requirements.lock are reused.

Source secret scan currently checks checkout contents, not the complete Git
history. Add history scanning/negative gate evidence before final acceptance.
No successful CI run, negative gate demonstration or continuous deployment has
yet been evidenced. Current cloud note must be preserved.

## Next delivery stage

Add needs dependencies on ALL checks, exact tested-image transfer to delivery,
GitHub OIDC authentication restricted to the trusted repository/branch and
narrowly scoped ACR/AKS rights. No mutable tag-only deployment or rebuild after
scanning. Never authenticate cloud delivery from a fork pull request.
AKS API remains developer-IP restricted. Choose/document a deployment path that
does not grant broad arbitrary runner-IP access. Run Command is a possible ARM
path but effectively powerful inside the cluster despite narrow Azure action
scope; evaluate and explain before provisioning CI roles.

Verify actual GitHub OIDC subject prefix before Entra federation: repositories
created/renamed after July15,2026 may use owner/repository IDs in the subject.
Use GitHub's OIDC customization API; do not assume the old name-only form.
