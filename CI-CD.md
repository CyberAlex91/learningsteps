# CI/CD preparation

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
