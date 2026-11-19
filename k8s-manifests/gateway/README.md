# HTTPS gateway preparation — not deployed

## Public HTTPS acceptance passed (2026-11-19)

User confirmed check_https_access.py passes public trust/hostname verification,
docs and readiness200, anonymous entries401 and HTTP-to-HTTPS redirect. Evidence
../artifacts/azure/https-access-check.json. Success followed ConfigMap router
rename/hot reload with no gateway restart after public routing had converged.
This supports the startup timing diagnosis. Automatic first-start handling in
deploy/recovery script remains required before claiming repeatable rebuild.

Next: configure_https_login.py previews the exact new Entra SPA callback;
--apply adds it to LearningSteps-Alex-Swagger, preserving existing localhost URLs.
Tenant and application/client object IDs checked; no new permission/client secret.
Interactive HTTPS Entra login and note CRUD are not yet verified.

## Selected deployment: Traefik (scan passed, rollout pending)

Update: gateway rollout/PVC Bound/public IP confirmed by user. HTTPS acceptance
still pending. Initial ACME request failed while public HTTP was not reachable;
HTTP redirect now works. On restart Traefik rejected /data/acme.json mode0660
(requires0600), disabling the resolver. Gateway command now sets umask077 and
chmod0600 on an existing ACME file before exec. The existing UID10001 owns the
file it created; no root process or secret download is needed. This runs after
each volume mount and preserves account/certificate contents. Apply the updated
manifest and verify rollout/TLS. Do not delete the PVC or ACME account file.

Next observed result: chmod fixed the resolver permission failure, but ACME
validation seven seconds after pod startup received connection refused. Public
HTTP redirect had worked between restarts. Suspected startup race with the
Local external traffic policy and Azure backend health convergence; not yet
proven by an external challenge. Avoid further repeated restarts. Dynamic router
renamed learningsteps-public to trigger a file-provider update/new certificate
attempt in the existing pod after the public route has converged. Apply ConfigMap
without rollout restart, allow mounted ConfigMap propagation, inspect logs.
If this confirms the race, automate a post-readiness ACME activation/retry in
the deployment/recovery workflow; first deployment cannot rely on a manual step.

User confirmed v2.11.61 at digest
sha256:262ccbae7ee89fbc17b2ec1c2c4718b48d4b4a7a38c8c26a8593b074fdbc7844:
zero HIGH/CRITICAL in OS and binary. traefik.yaml is the current deployable
manifest; Caddyfile is historical rejected-candidate configuration only.

deploy_https_gateway.sh verifies context/subscription/local digest, uploads the
unchanged image to ACR, compares registry digest, validates resources server-side
then applies only traefik.yaml. Creates project StorageClass, 4Gi StandardSSD_LRS
PVC/disk, public-only ConfigMap, one hardened gateway Deployment and LoadBalancer
Service using existing pip-learningsteps-https. Disk allocation and networking
can add charges. No new node, Azure identity, RBAC grant or database is created.

Traefik uses ports 8080/8443 and private probe port 8082, no dashboard/access log,
Kubernetes API or Docker socket. Standard HTTP-01 ACME automatic issuance and
renewal writes private material to /data/acme.json; keep that persistent volume
and never export it. Public port80 performs ACME challenges and HTTPS redirects;
explicit :443 redirect avoids redirecting clients to internal port8443.
Gateway readiness means process responsiveness, not completed certificate issuance.
Run check_https_access.py afterward to verify public CA trust and correct hostname,
HTTP redirect, docs/readiness200 and anonymous entries401. It retries convergence
for five minutes without disabling TLS. Entra HTTPS callback/login still pending.

The single gateway/Recreate strategy is a lab availability limitation and avoids
RWO disk contention; two API replicas remain behind it. During final cleanup,
delete public Kubernetes Service and PVC before AKS; ordinary pauses keep PVC.
Do not recursively apply this directory; Caddy candidate is unapproved.

## Earlier candidate investigation

Update 2026-11-19: Caddy candidate failed the mandatory scan (two HIGH Go
dependency findings). Caddyfile below is an unused candidate, not a deployable
approved configuration. Released Traefik v2.11.61 is the next candidate because
its source declares fixes for both findings. Run scripts/scan_gateway.sh before
preparing its configuration. Keep the same public IP, backend and certificate
storage design; no Azure resources need replacing. Traefik would use a file
provider without Kubernetes/Docker discovery, dashboard or Azure credentials.

Hostname confirmed by Terraform output:
learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com.
Static Standard IP pip-learningsteps-https is created in
rg-learningsteps-evolution-nodes; subsequent Terraform plan No changes.

Use the official Caddy Alpine image, verify digest and HIGH/CRITICAL gate before
deployment. Caddyfile uses high ports 8080/8443 for non-root operation; public
LoadBalancer maps 80/443 to these ports. External port 80 is needed for ACME
and HTTPS redirect; the API must not be served as public plaintext HTTP.
Port 8081 is a pod-only gateway probe, not a public Service port.
Disable Caddy admin API, keep access logging disabled (no bearer-token logging),
use only HTTP/1.1 and HTTP/2 to avoid unused UDP/HTTP3 exposure.

Gateway will have no Azure identity, Key Vault mount or database credentials.
It sees proxied HTTP traffic as TLS terminator. A persistent Azure Disk volume
must store /data (certificates and private keys); /config may be emptyDir because
the Caddyfile is declarative. Never export certificate keys into artifacts/Git.
One gateway replica/Recreate strategy avoids concurrent RWO disk attachment;
this is a deliberate lab availability limitation, not gateway high availability.
Two independent API replicas and HPA remain in place behind the gateway.

Expected additional cost: managed disk plus public LoadBalancer/IP usage.
IP already created; disk/LoadBalancer service not yet created. Kubernetes CSI
creates the disk from PVC, so cleanup/rebuild must handle Kubernetes objects
before deleting AKS. Do not delete certificate volume during ordinary pauses.

After image approval: create PVC, ConfigMap, gateway Deployment and LoadBalancer
referencing azure-pip-name and azure-load-balancer-resource-group annotations.
Verify DNS, certificate chain, HTTPS responses and HTTP redirect, then add the
exact HTTPS Swagger SPA callback to Entra while preserving localhost callback.
Finally test authenticated own-note CRUD. Foundry cloud feature is still pending.
