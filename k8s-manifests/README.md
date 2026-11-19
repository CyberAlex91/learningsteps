# LearningSteps Kubernetes configuration

## Application rollout prepared (not yet applied)

configmap.yaml holds public identifiers and the credential-file path only.
deployment.yaml uses the tested runtime image digest, two initial replicas,
Workload Identity/CSI, non-root/read-only restrictions and bounded probes.
service.yaml is the internal backend; the required public LoadBalancer belongs
to a separate HTTPS gateway still to be configured. HPA targets 60% CPU of the
100m request, two to four replicas. Metrics availability and scaling are not yet
verified. Do not describe autoscaling or a public application as complete.

Upload the unchanged tested image first and compare registry digest with the
deployment. Apply these four application files explicitly after reviewing them;
never recursively apply diagnostics or the unrendered workload-access template.
Public auth ConfigMap file uses subPath and configuration is read at startup:
restart rollout after config changes. Initial replicas is a bootstrap setting;
later CI image updates should preserve the HPA-managed replica count.

## Runtime identity acceptance (passed 2026-11-19)

User confirmed CSI mount, restricted SQL app login/read-only query with TLSv1.3
and explicit denial of the admin secret by Key Vault RBAC. Evidence saved as
../artifacts/azure/workload-access-check.json; diagnostic pod removed. Initial
file permission issue was fixed as described below.

Run `python3 app/scripts/check_workload_access.py` from LearningSteps in WSL.
It checks context/subscription, reads only the public managed identity client ID,
renders workload-access.json and applies the reusable ServiceAccount and
SecretProviderClass. Do not apply that template without rendering its placeholder.
JSON is a supported Kubernetes manifest format. No secretObjects sync is used.
The CSI file uses 0444: read-only for the non-root process in the explicitly
mounted pod volume. An initial 0440 test failed with PermissionError: the mounted
file's group did not grant the application access despite pod fsGroup. This
does not grant other pods a mount or any Azure rights. Do not add untrusted
sidecars to a pod that has this credential mount.

The diagnostic pod uses the API service account, workload identity webhook and
read-only CSI mount. It connects using the mounted URL (verify-full), checks
app login, TLS and entry count with read-only SQL, then obtains a workload token
and requires an explicit ForbiddenByRbac response when requesting the admin
secret. A generic network 403 is not accepted as proof of access isolation.
No credential values or tokens are printed/saved; no host Azure login is mounted.
Metadata evidence is saved outside Git, diagnostic pod removed, SA/SPC retained
for the eventual deployment. Failure stops the run; do not broaden permissions.
This does not deploy the API or implement DATABASE_URL_FILE in the application.

## Private network acceptance passed

User applied the namespace and network diagnostic. Pod reached Succeeded and
reported DNS 10.62.1.4, TCP 5432 reachable and verified TLSv1.3. No login/SQL was
performed in that test. AKS was accidentally stopped during earlier pause
discussion, then restarted successfully; two replacement nodes report Ready.
No pause is currently requested; keep working until the user says to pause.

## Read-only login test prepared (not run)

Update: user ran this test successfully. Admin login and metadata SELECT used
verified TLSv1.3, metadata evidence saved, diagnostic pod removed. This confirms
actual private authentication, not only the earlier network handshake.

## Cloud schema and app SQL role setup passed

User ran configure_cloud_database.py successfully on 2026-11-18. Schema and
restricted role configured; entry count remained 0; actual app password login
and SELECT used TLSv1.3; all DML grants verified and CREATE TABLE rejected.
Evidence: ../artifacts/azure/cloud-database-schema-check.json. Setup pod removed.

`python3 app/scripts/configure_cloud_database.py` reuses the hardened diagnostic
pod, captures both vault credentials in memory/stdin, and initializes only the
dedicated cloud learningsteps database. It reuses database_setup.sql without
its psql display command and adds database/cloud_access.sql for additive owner
columns and explicit grants. It never assigns legacy notes to an owner or
updates/deletes entries. Before/after row counts must agree.

The setup creates learningsteps_app if absent, refuses elevated roles or role
memberships, and grants only CONNECT, schema USAGE and table SELECT/INSERT/
UPDATE/DELETE. Public database/schema/table privileges are revoked. Password
comes from the existing app vault secret; libpq computes a SCRAM verifier before
ALTER ROLE, avoiding a plaintext SQL password literal. Setup stops if statement,
duration, sampled-duration or pgaudit logging is enabled. Raw database errors
and credential values are not printed. The setup does not use the Terraform
provider to initialize SQL, so SQL password values do not enter Terraform state.

It verifies real app login/TLS, SELECT and all four DML grants and deliberately
tests denied CREATE TABLE inside a savepoint. No notes are inserted or removed.
If setup fails after schema commit, rerun deliberately after diagnosing; it uses
the same persisted credentials. App per-user filtering remains the API's job;
SQL role permissions alone are not per-user row isolation.
The final Workload Identity/Key Vault CSI integration is still pending.

Run `python3 app/scripts/check_private_db_login.py` from LearningSteps in WSL.
The helper checks the current context, creates the named hardened pod, waits
for readiness, captures the admin password from Key Vault only in memory,
and transmits it through stdin of kubectl exec (TLS Kubernetes API transport).
No Kubernetes Secret or password in command arguments, file or logs is created.
The pod executes one read-only pg_stat_ssl/current_database/current_user query
over certificate-verified TLS; no schema changes or notes. The helper saves
only allowlisted metadata under ../artifacts/azure and deletes only its own pod.
No Azure credentials are supplied to the pod. This is a developer diagnostic,
not the final application Workload Identity/Key Vault integration.

## Original network test procedure

Apply namespace.yaml and diagnostics/db-network-check.yaml explicitly; do not
recursively apply this directory as routine deployment. Diagnostic pods are not
part of the application's eventual rollout.

The namespace enforces Kubernetes Restricted Pod Security v1.36. The diagnostic
uses the existing scanned ACR image by immutable digest, without credentials or
service-account token. It runs once, as non-root, with read-only root filesystem,
no extra Linux capabilities, no privilege escalation and RuntimeDefault seccomp.

It verifies private DNS returns only 10.62.1.0/24 addresses, opens TCP 5432 from
an ordinary pod network, sends the PostgreSQL SSLRequest and verifies certificate
chain and hostname using system CAs and TLS >=1.2. It never authenticates or runs
SQL. Completion therefore does not prove SQL permissions or schema readiness.
It also exercises the node identity's AcrPull permission.

Wait for phase Succeeded, save logs outside the repository under artifacts,
and delete only the named completed diagnostic pod afterward. Keep the namespace
for subsequent application manifests. If it fails, inspect logs and pod events;
do not disable TLS verification, make the database public or broaden firewall
rules without establishing the actual cause.
