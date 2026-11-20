# Zweck: Sichert und entfernt alle kostenpflichtigen LearningSteps-Ressourcen und stellt sie einschließlich Remote-State-Backend wieder her.
"""WSL: python3 app/scripts/lifecycle.py down | up | status | check.

The scope is this project's five exact resource groups, never the subscription.
Private checkpoints, encrypted state and backup keys must stay on this machine.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import recovery

ROOT, APP, SUB = recovery.ROOT, recovery.APP, recovery.SUB
INFRA = APP / "infra-terraform"
CONTROL = ROOT / ".state/lifecycle.json"
GROUPS = ("rg-learningsteps-ai", "rg-learningsteps-data", "rg-learningsteps-evolution",
          "rg-learningsteps-evolution-nodes", "rg-learningsteps-tfstate")
STATE_RG, STORAGE = GROUPS[-1], "lsstatealex0ad5f630"
REPO = "CyberAlex91/learningsteps"


def now():
    return datetime.now(timezone.utc).isoformat()


def command(args, *, input=None, timeout=900, allowed=(0,)):
    result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if result.returncode not in allowed:
        raise RuntimeError("Command failed: " + Path(args[0]).name + " " + args[1] + "; raw output withheld")
    return result.stdout.strip()


def az(*args):
    return json.loads(command(["az", *args, "--subscription", SUB, "-o", "json", "--only-show-errors"]))


def tf(*args, **kwargs):
    return command(["terraform", "-chdir=" + str(INFRA), *args], **kwargs)


def save(context):
    CONTROL.parent.mkdir(exist_ok=True)
    temporary = CONTROL.with_suffix(".tmp")
    temporary.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, CONTROL)


def group_exists(name):
    if name not in GROUPS:
        raise RuntimeError("Group outside project scope")
    return az("group", "exists", "--name", name)


def verify_account():
    account = json.loads(command(["az", "account", "show", "-o", "json"]))
    if account["id"] != SUB or account["tenantId"] != "c0531484-50fa-4ff2-97df-b1f2d4810603":
        raise RuntimeError("Select Alexander Plank - Sub in the project tenant")


def project_inventory(resources):
    return [r for r in resources if r["resourceGroup"].lower() in GROUPS
            or str((r.get("tags") or {}).get("project", "")).lower() == "learningsteps"]


def audit_off():
    resources = project_inventory(az("resource", "list"))
    groups = {name: group_exists(name) for name in GROUPS}
    result = {"checked_at": now(), "passed": not resources and not any(groups.values()),
              "active_project_resource_count": len(resources), "groups_exist": groups,
              "scope": "LearningSteps only; other subscription resources not modified",
              "soft_deleted_services_may_remain": True, "billing_ledger_queried": False}
    if not result["passed"]:
        raise RuntimeError("Project resources remain; do not claim a completed cost shutdown")
    return result


def validate_release(release):
    manifest = (ROOT / release["data_backup"]).resolve()
    if not manifest.is_relative_to(ROOT / "artifacts/backups"):
        raise RuntimeError("Manifest outside project backup directory")
    info = json.loads(manifest.read_text(encoding="utf-8"))
    if not info.get("isolated_restore_verified"):
        raise RuntimeError("An actual isolated restore verification is required")
    encrypted = (ROOT / info["encrypted_file"]).resolve()
    key_file = (ROOT / info["key_file"]).resolve()
    if not encrypted.is_relative_to(ROOT / "artifacts/backups") or not key_file.is_relative_to(ROOT / ".secrets/backups"):
        raise RuntimeError("Backup paths outside private project directories")
    blob = encrypted.read_bytes(); key = key_file.read_bytes()
    if recovery.sha(encrypted) != info["encrypted_sha256"] or not blob.startswith(b"LSBACKUP1"):
        raise RuntimeError("Data backup integrity failure")
    rows = json.loads(AESGCM(key).decrypt(blob[9:21], blob[21:], b"learningsteps-entries-v1"))
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if digest != info["data_sha256"] or digest != release["data_sha256"] or len(rows) != info["count"]:
        raise RuntimeError("Decrypted data hash mismatch")
    for image in release["images"].values():
        archive = (ROOT / image["archive"]).resolve()
        if not archive.is_relative_to(ROOT / "artifacts/recovery") or recovery.sha(archive) != image["archive_sha256"]:
            raise RuntimeError("Image archive mismatch")
    cert = release["certificates"]; path = (ROOT / cert["file"]).resolve()
    if not path.is_relative_to(ROOT / "artifacts/recovery") or recovery.sha(path) != cert["sha256"]:
        raise RuntimeError("Certificate archive mismatch")
    blob = path.read_bytes()
    certificates = json.loads(AESGCM(key).decrypt(blob[8:20], blob[20:], b"learningsteps-acme-v1"))
    if not any(c.get("domain", {}).get("main") == recovery.HOST for c in certificates.get("letsencrypt", {}).get("Certificates", [])):
        raise RuntimeError("Certificate archive contains no matching hostname")
    return info, key


def encrypted_state(context, name):
    release = json.loads(recovery.RELEASE.read_text(encoding="utf-8"))
    _, key = validate_release(release)
    state = tf("state", "pull")
    parsed = json.loads(state)
    nonce = os.urandom(12)
    directory = ROOT / ".secrets/backups/lifecycle" / context["cycle"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + ".enc")
    encrypted = b"LSSTATE1" + nonce + AESGCM(key).encrypt(nonce, state.encode(), b"learningsteps-state-v1")
    path.write_bytes(encrypted); path.chmod(0o600)
    assert json.loads(AESGCM(key).decrypt(encrypted[8:20], encrypted[20:], b"learningsteps-state-v1")) == parsed
    context[name] = {"file": path.relative_to(ROOT).as_posix(), "sha256": recovery.sha(path),
                     "resource_count": len(parsed.get("resources", []))}
    save(context)
    return parsed


def cloud_delivery(enabled):
    command(["gh", "variable", "set", "LEARNINGSTEPS_CLOUD_ENABLED", "--repo", REPO,
             "--body", "true" if enabled else "false"])


def ensure_docker():
    try:
        command([recovery.DOCKER, "info", "--format", "{{.ServerVersion}}"], timeout=20)
        return
    except (RuntimeError, subprocess.TimeoutExpired):
        print("Starting local Docker Desktop for image backup/restore...", flush=True)
    command(["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "Start-Process -FilePath 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\DockerDesktop\\Docker Desktop.exe' -WindowStyle Hidden"], timeout=45)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            command([recovery.DOCKER, "info", "--format", "{{.ServerVersion}}"], timeout=20)
            return
        except (RuntimeError, subprocess.TimeoutExpired):time.sleep(5)
    raise RuntimeError("Docker Desktop did not become ready; open it and retry")


def refresh_ip():
    with urlopen("https://api.ipify.org", timeout=15) as response:
        address = ipaddress.IPv4Address(response.read(128).decode().strip())
    if not address.is_global:
        raise RuntimeError("Expected global developer IPv4")
    path = INFRA / "aks.local.auto.tfvars.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    previous_cidr = data.get("aks_api_allowed_cidr")
    data["aks_api_allowed_cidr"] = str(address) + "/32"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if group_exists("rg-learningsteps-evolution") and any(v["name"] == "kv-lsteps-0ad5f630" for v in az("keyvault", "list", "-g", "rg-learningsteps-evolution")):
        command(["az", "keyvault", "network-rule", "add", "--name", "kv-lsteps-0ad5f630", "--resource-group", "rg-learningsteps-evolution",
                 "--ip-address", data["aks_api_allowed_cidr"], "--subscription", SUB, "-o", "none"])
    return previous_cidr != data["aks_api_allowed_cidr"]


def start_for_backup():
    for service, group, name in [("aks", "rg-learningsteps-evolution", "aks-learningsteps-evolution"),
                                 ("postgres", "rg-learningsteps-data", "psql-learningsteps-alex-0ad5f630")]:
        prefix = [service] if service == "aks" else [service, "flexible-server"]
        obj = az(*prefix, "show", "-g", group, "-n", name)
        stopped = obj.get("powerState", {}).get("code") == "Stopped" if service == "aks" else obj["state"] == "Stopped"
        if stopped:
            command(["az", *prefix, "start", "-g", group, "-n", name, "--subscription", SUB, "--no-wait"])
        deadline = time.monotonic() + 1200
        while True:
            obj = az(*prefix, "show", "-g", group, "-n", name)
            ready = obj.get("provisioningState") == "Succeeded" and obj.get("powerState", {}).get("code") == "Running" if service == "aks" else obj["state"] == "Ready"
            if ready:break
            if time.monotonic() > deadline:raise RuntimeError("Service start timeout")
            time.sleep(15)
    refresh_ip()
    tf("plan", "-out=lifecycle-ip.tfplan", "-no-color")
    plan = json.loads(tf("show", "-json", "lifecycle-ip.tfplan"))
    for change in plan.get("resource_changes", []):
        if change["change"]["actions"] == ["no-op"]:continue
        if change["address"] not in ("azurerm_key_vault.evolution", "azurerm_kubernetes_cluster.evolution") or change["change"]["actions"] != ["update"]:
            raise RuntimeError("Unexpected infrastructure changes before backup")
    tf("apply", "-no-color", "lifecycle-ip.tfplan", timeout=1800)
    command(["az", "aks", "get-credentials", "-g", "rg-learningsteps-evolution", "-n", "aks-learningsteps-evolution",
             "--file", os.environ["KUBECONFIG"], "--overwrite-existing", "--format", "exec", "--subscription", SUB])
    command(["kubelogin", "convert-kubeconfig", "-l", "azurecli"])


def step(context, number, description, operation):
    if context.get("down_step", 0) >= number:return
    print(description, flush=True); operation()
    context["down_step"] = number; context["updated_at"] = now(); save(context)


def down(context):
    if context.get("phase") == "down":
        print(json.dumps(audit_off(), indent=2));return
    if context.get("phase") == "up" and not context.get("up_verified_at"):
        raise RuntimeError("Restore is incomplete; preserve its checkpoints and resume up before a new down cycle")
    if context.get("phase") not in (None, "down-in-progress", "up"):
        raise RuntimeError("Unexpected lifecycle state")
    if context.get("phase") != "down-in-progress":
        context.clear(); context.update(cycle=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6], phase="down-in-progress", down_step=0)
        save(context)

    def maintenance_backup():
        cloud_delivery(False)
        runs = json.loads(command(["gh", "run", "list", "--repo", REPO, "--limit", "30", "--json", "status"]))
        if any(r["status"] != "completed" for r in runs):
            raise RuntimeError("Wait for active GitHub runs before teardown; cloud delivery is disabled")
        ensure_docker()
        start_for_backup()
        k = recovery.k
        k("delete", "hpa", "learningsteps-api", "-n", "learningsteps", "--ignore-not-found")
        k("scale", "deployment/learningsteps-api", "-n", "learningsteps", "--replicas=0")
        k("wait", "--for=delete", "pod", "-l", "app=learningsteps-api", "-n", "learningsteps", "--timeout=180s")
        cluster = az("aks", "show", "-g", "rg-learningsteps-evolution", "-n", "aks-learningsteps-evolution")
        uid = k("get", "namespace", "learningsteps", "-o", "jsonpath={.metadata.uid}")
        (ROOT / "artifacts/azure/before-infrastructure-recovery.json").write_text(json.dumps({"namespace_uid": uid, "fqdn": cluster["fqdn"], "oidc": cluster["oidcIssuerProfile"]}, indent=2) + "\n")
        if "backup" not in context:
            before = set((ROOT / "artifacts/backups").glob("*.json"))
            command(["python3", str(APP / "scripts/cloud_data_backup.py"), "backup"])
            added = set((ROOT / "artifacts/backups").glob("*.json")) - before
            if len(added) != 1:raise RuntimeError("Expected one fresh backup manifest")
            context["backup"] = next(iter(added)).relative_to(ROOT).as_posix();save(context)
        manifest = ROOT / context["backup"]
        command(["python3", str(APP / "scripts/cloud_data_backup.py"), "check", "--manifest", str(manifest)])
        command(["python3", str(APP / "scripts/cloud_data_backup.py"), "verify-current", "--manifest", str(manifest)])
        if recovery.RELEASE.exists():
            previous = json.loads(recovery.RELEASE.read_text())
            if previous["data_backup"] != context["backup"]:
                history = ROOT / ".state/releases";history.mkdir(exist_ok=True)
                recovery.RELEASE.rename(history / (context["cycle"] + "-previous.json"))
        if not recovery.RELEASE.exists():recovery.prepare(manifest.resolve())
        validate_release(json.loads(recovery.RELEASE.read_text()))
        encrypted_state(context, "state-before-destroy")

    step(context, 1, "Preparing current verified data/image/certificate backups...", maintenance_backup)

    def remove_gateway():
        k = recovery.k
        pv = k("get", "pvc", "learningsteps-https-data", "-n", "learningsteps", "--ignore-not-found", "-o", "jsonpath={.spec.volumeName}")
        k("delete", "service", "learningsteps-https", "-n", "learningsteps", "--ignore-not-found")
        k("delete", "deployment", "learningsteps-https", "-n", "learningsteps", "--ignore-not-found", "--timeout=180s")
        k("delete", "pvc", "learningsteps-https-data", "-n", "learningsteps", "--ignore-not-found", "--timeout=180s")
        if pv:k("wait", "--for=delete", "pv/" + pv, "--timeout=240s")

    step(context, 2, "Releasing gateway LoadBalancer and certificate disk...", remove_gateway)

    def destroy_application():
        if tf("state", "list").strip():
            recovery.destroy_plan()
            summary = json.loads((ROOT / "artifacts/azure/evolution-destroy-plan.json").read_text())
            if recovery.sha(INFRA / "evolution-destroy.tfplan") != summary["plan_sha256"]:
                raise RuntimeError("Destroy plan checksum mismatch")
            addresses = set(context.get("destroy_addresses", [])) | {r["address"] for r in summary["deletions"]}
            context["destroy_addresses"] = sorted(addresses)
            context["destroyed_resources"] = max(context.get("destroyed_resources", 0), len(addresses));save(context)
            tf("apply", "-no-color", "evolution-destroy.tfplan", timeout=3600)
        if tf("state", "list").strip():raise RuntimeError("Managed state not empty after destroy")
        encrypted_state(context, "state-empty")
        guard = ROOT / ".state/evolution-guards.json"
        if guard.exists():recovery.restore_guards()
        receipt = {"checked_at": now(), "managed_resources_remaining": 0, "destroyed_resources": context["destroyed_resources"],
                   "resource_groups_exist": {g: group_exists(g) for g in GROUPS}, "execution": "checksum-verified Terraform destroy plan"}
        (ROOT / "artifacts/azure/terraform-destroy-check.json").write_text(json.dumps(receipt, indent=2) + "\n")

    step(context, 3, "Applying reviewed project-only Terraform destroy plan...", destroy_application)

    def remove_backend():
        validate_release(json.loads(recovery.RELEASE.read_text(encoding="utf-8")))
        for group in GROUPS:
            if group_exists(group):
                obj = az("group", "show", "--name", group)
                if str((obj.get("tags") or {}).get("project", "")).lower() != "learningsteps":
                    raise RuntimeError("Unexpected group ownership; no deletion")
                if group == STATE_RG:
                    for name in ("state-before-destroy", "state-empty"):
                        snapshot = context[name]
                        if recovery.sha(ROOT / snapshot["file"]) != snapshot["sha256"]:
                            raise RuntimeError("Private offline state backup mismatch")
                command(["az", "group", "delete", "--name", group, "--subscription", SUB, "--yes"], timeout=1800)
        receipt = audit_off(); receipt.update(cycle=context["cycle"], data_backup=context["backup"], backend_removed=True)
        (ROOT / "artifacts/azure/lifecycle-down-check.json").write_text(json.dumps(receipt, indent=2) + "\n")

    step(context, 4, "Removing remaining project groups including the state storage account...", remove_backend)
    context["phase"] = "down";context["completed_at"] = now();save(context)
    print("PASS: no active LearningSteps resources remain; offline recovery bundle verified", flush=True)


def backend():
    print("Creating protected Entra remote-state backend...", flush=True)
    if group_exists(STATE_RG):
        group = az("group", "show", "--name", STATE_RG)
        if (group.get("tags") or {}).get("project") != "LearningSteps":
            raise RuntimeError("Existing backend group is not owned by this project")
    command(["az", "group", "create", "--name", STATE_RG, "--location", "germanywestcentral", "--tags", "project=LearningSteps", "purpose=TerraformState", "--subscription", SUB, "-o", "none"])
    command(["az", "storage", "account", "create", "--name", STORAGE, "--resource-group", STATE_RG, "--location", "germanywestcentral",
             "--kind", "StorageV2", "--sku", "Standard_LRS", "--https-only", "true", "--min-tls-version", "TLS1_2",
             "--allow-blob-public-access", "false", "--allow-shared-key-access", "false", "--tags", "project=LearningSteps", "--subscription", SUB, "-o", "none"])
    oid = json.loads(command(["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "json"]))
    scope = "/subscriptions/" + SUB + "/resourceGroups/" + STATE_RG + "/providers/Microsoft.Storage/storageAccounts/" + STORAGE
    roles = az("role", "assignment", "list", "--scope", scope)
    if not any(r["principalId"] == oid and r.get("roleDefinitionName") == "Storage Blob Data Contributor" for r in roles):
        command(["az", "role", "assignment", "create", "--assignee-object-id", oid, "--assignee-principal-type", "User", "--role", "Storage Blob Data Contributor", "--scope", scope, "--subscription", SUB, "-o", "none"])
    deadline = time.monotonic() + 600
    while True:
        try:
            command(["az", "storage", "container", "create", "--name", "tfstate", "--account-name", STORAGE, "--auth-mode", "login", "--public-access", "off", "--subscription", SUB, "-o", "none"]);break
        except RuntimeError:
            if time.monotonic() > deadline:raise
            time.sleep(15)
    command(["az", "storage", "account", "blob-service-properties", "update", "--account-name", STORAGE, "-g", STATE_RG, "--subscription", SUB,
             "--enable-versioning", "true", "--enable-delete-retention", "true", "--delete-retention-days", "7", "--enable-container-delete-retention", "true", "--container-delete-retention-days", "7", "-o", "none"])
    tf("init", "-reconfigure", "-input=false", "-no-color")
    existing = tf("state", "pull", allowed=(0, 1))
    if not existing.strip().startswith("{"):
        context = json.loads(CONTROL.read_text())
        snapshot = context["state-empty"]
        if snapshot["resource_count"] != 0 or recovery.sha(ROOT / snapshot["file"]) != snapshot["sha256"]:
            raise RuntimeError("Verified empty state snapshot required")
        release = json.loads(recovery.RELEASE.read_text());_, key = validate_release(release)
        blob = (ROOT / snapshot["file"]).read_bytes()
        state = AESGCM(key).decrypt(blob[8:20], blob[20:], b"learningsteps-state-v1")
        if json.loads(state).get("resources"):
            raise RuntimeError("Never restore the pre-destroy resource state after deleting resources")
        path = (ROOT / snapshot["file"]).with_suffix(".restore.tfstate")
        try:
            path.write_bytes(state);path.chmod(0o600)
            tf("state", "push", str(path))
        finally:path.unlink(missing_ok=True)
    account = az("storage", "account", "show", "--name", STORAGE, "-g", STATE_RG,
                 "--query", "{HTTPS:enableHttpsTrafficOnly,SharedKeys:allowSharedKeyAccess,PublicBlobs:allowBlobPublicAccess}")
    if account != {"HTTPS": True, "SharedKeys": False, "PublicBlobs": False}:
        raise RuntimeError("Remote-state account security settings do not match")
    (ROOT / "artifacts/azure/backend-recreation-check.json").write_text(json.dumps({"passed": True, "checked_at": now(), "security": account,
        "state_readable": isinstance(json.loads(tf("state", "pull")), dict), "credentials_printed": False}, indent=2) + "\n")


def up(context):
    if context.get("phase") == "up" and context.get("up_verified_at"):
        print("Already restored; use status to inspect the current resources");return
    if context.get("phase") not in ("down", "up"):
        raise RuntimeError("A completed down cycle is required before up")
    release = json.loads(recovery.RELEASE.read_text(encoding="utf-8"));validate_release(release)
    ensure_docker()
    if context["phase"] == "down":
        # Reset only once per NEW infrastructure cycle, not on bootstrap retries.
        for key in ("database_restored", "bootstrap_verified_at", "restored_images"):
            release.pop(key, None)
        recovery.save(release);context["phase"] = "up";context["up_step"] = 0;save(context)
    cloud_delivery(False)
    if context.get("up_step", 0) < 1:
        backend();context["up_step"] = 1;save(context)
    ip_changed = refresh_ip()
    if context.get("up_step", 0) < 2 or ip_changed:
        recovery.infrastructure();context["up_step"] = 2;save(context)
    if context.get("up_step", 0) < 3:
        recovery.bootstrap(json.loads(recovery.RELEASE.read_text()));context["up_step"] = 3;save(context)
    if (ROOT / ".state/evolution-guards.json").exists():recovery.restore_guards()
    command(["python3", str(APP / "scripts/check_recovery_final.py")], timeout=1800)
    cloud_delivery(True);context["up_verified_at"] = now();save(context)
    print("PASS: infrastructure, preserved notes, HTTPS and keyless AI restored; CI delivery enabled")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("down", "up", "status", "check"))
    args = parser.parse_args()
    if os.name != "posix":raise RuntimeError("Run in WSL")
    # One lifecycle writer at a time, including while child tools are running.
    import fcntl
    CONTROL.parent.mkdir(exist_ok=True)
    lifecycle_lock = CONTROL.with_suffix(".lock").open("a+")
    if args.mode in ("down", "up"):
        try:fcntl.flock(lifecycle_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError("Another lifecycle command is running") from None
    os.environ["PATH"] = str(Path.home() / ".local/share/learningsteps-tools/bin") + ":" + os.environ["PATH"]
    os.environ["KUBECONFIG"] = str(Path.home() / ".kube/learningsteps-evolution.yaml")
    context = json.loads(CONTROL.read_text()) if CONTROL.exists() else {}
    if args.mode == "check":
        release = json.loads(recovery.RELEASE.read_text());info, _ = validate_release(release)
        print("PASS: encrypted data, key, verified restore, image archives and certificate ciphertext; notes=" + str(info["count"]));return
    verify_account()
    if args.mode == "status":
        resources = project_inventory(az("resource", "list"))
        print(json.dumps({"phase": context.get("phase", "not recorded"), "active_project_resources": [{"name": r["name"], "type": r["type"], "group": r["resourceGroup"]} for r in resources]}, indent=2));return
    (down if args.mode == "down" else up)(context)


if __name__ == "__main__":
    try:main()
    except Exception as error:
        print("STOP: " + (str(error) if type(error) is RuntimeError else type(error).__name__) + "; private values/raw errors withheld", flush=True)
        raise SystemExit(1) from None
