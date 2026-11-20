# Zweck: Sichert den getesteten Release und baut Anwendung, Daten und HTTPS nach Terraform-Neuaufbau reproduzierbar auf.
"""Run in WSL: prepare --backup PATH, then bootstrap after reviewed Terraform apply."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPRedirectHandler

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import yaml

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
RELEASE = ROOT / ".state/evolution-release.json"
SUB = "0ad5f630-c506-401a-93fa-36b0fe313829"
REGISTRY = "acrlearningstepsalex0ad5f630"
SERVER = REGISTRY + ".azurecr.io"
HOST = "learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com"
DOCKER = "/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"


def run(args, *, input=None, timeout=600):
    result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Failed command: " + Path(args[0]).name + " " + (args[1] if len(args) > 1 else "") + "; raw output withheld")
    return result.stdout.strip()


def k(*args, **kwargs):
    request_timeout = "0" if args and args[0] in ("rollout", "wait") else "30s"
    return run(["kubectl", "--request-timeout=" + request_timeout, *args], **kwargs)


def save(data):
    RELEASE.parent.mkdir(exist_ok=True)
    temporary = RELEASE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RELEASE)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def login():
    token = run(["az", "acr", "login", "--name", REGISTRY, "--subscription", SUB,
                 "--expose-token", "--query", "accessToken", "-o", "tsv"])
    run([DOCKER, "login", SERVER, "--username", "00000000-0000-0000-0000-000000000000", "--password-stdin"], input=token)


def prepare(backup):
    if RELEASE.exists():
        raise RuntimeError("Release manifest already exists; review it rather than overwrite")
    info = json.loads(backup.read_text())
    if not info.get("isolated_restore_verified"):
        raise RuntimeError("Isolated data restore not verified")
    if sha(ROOT / info["encrypted_file"]) != info["encrypted_sha256"]:
        raise RuntimeError("Backup checksum mismatch")
    if k("config", "current-context") != "aks-learningsteps-evolution":
        raise RuntimeError("Wrong cluster context")
    release = {"prepared_at": datetime.now(timezone.utc).isoformat(), "data_backup": str(backup.relative_to(ROOT)),
               "data_sha256": info["data_sha256"], "images": {}, "source_commit": run(["git", "-C", str(APP), "rev-parse", "HEAD"])}
    directory = ROOT / "artifacts/recovery" / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex())
    directory.mkdir(parents=True, exist_ok=True)
    login()
    for component, deployment, container in [("api", "learningsteps-api", "api"), ("gateway", "learningsteps-https", "gateway")]:
        obj = json.loads(k("get", "deployment", deployment, "-n", "learningsteps", "-o", "json"))
        reference = next(c["image"] for c in obj["spec"]["template"]["spec"]["containers"] if c["name"] == container)
        if not reference.startswith(SERVER + "/learningsteps-") or "@sha256:" not in reference:
            raise RuntimeError("Unexpected release image")
        print("Saving tested " + component + " image locally...", flush=True)
        run([DOCKER, "pull", "--platform", "linux/amd64", reference])
        index = json.loads(run([DOCKER, "buildx", "imagetools", "inspect", reference, "--raw"]))
        expected = reference.split("@", 1)[1]
        if "manifests" in index:
            matches = [m["digest"] for m in index["manifests"] if m.get("platform", {}).get("os") == "linux" and m["platform"].get("architecture") == "amd64"]
            if len(matches) != 1:raise RuntimeError("Ambiguous release platform")
            expected = matches[0]
        image_id = run([DOCKER, "image", "inspect", reference, "--format", "{{.Id}}"])
        archive = directory / (component + ".tar")
        run([DOCKER, "image", "save", "--output", run(["wslpath", "-w", str(archive)]), reference])
        release["images"][component] = {"source": reference, "platform_digest": expected, "image_id": image_id,
                                       "archive": archive.relative_to(ROOT).as_posix(), "archive_sha256": sha(archive)}
    # Capture certificate private material only into memory and AES-GCM ciphertext.
    acme = k("exec", "deployment/learningsteps-https", "-n", "learningsteps", "-c", "gateway", "--", "cat", "/data/acme.json")
    certificates = json.loads(acme).get("letsencrypt", {}).get("Certificates", [])
    if not any(c.get("domain", {}).get("main") == HOST for c in certificates):
        raise RuntimeError("Expected valid-host certificate backup")
    key = (ROOT / info["key_file"]).read_bytes(); nonce = os.urandom(12)
    encrypted = b"LSACME01" + nonce + AESGCM(key).encrypt(nonce, acme.encode(), b"learningsteps-acme-v1")
    target = directory / "certificates.enc"; target.write_bytes(encrypted)
    assert json.loads(AESGCM(key).decrypt(encrypted[8:20], encrypted[20:], b"learningsteps-acme-v1")) == json.loads(acme)
    release["certificates"] = {"file": target.relative_to(ROOT).as_posix(), "sha256": sha(target)}
    save(release)
    print("PASS: release archives/checksums and encrypted certificate backup verified")
    print("Release manifest: .state/evolution-release.json")


def apply_objects(objects):
    k("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "List", "items": objects}))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bootstrap(release):
    # Archives are checked BEFORE touching the cluster.
    for image in release["images"].values():
        if sha(ROOT / image["archive"]) != image["archive_sha256"]:
            raise RuntimeError("Release image archive mismatch")
    cert_info = release["certificates"]
    if sha(ROOT / cert_info["file"]) != cert_info["sha256"]:
        raise RuntimeError("Certificate archive mismatch")
    print("Restoring exact tested images to the recreated registry...", flush=True)
    login(); images = {}
    for name, image in release["images"].items():
        run([DOCKER, "image", "load", "--input", run(["wslpath", "-w", str(ROOT / image["archive"])])])
        repo = "learningsteps-" + ("api" if name == "api" else "gateway")
        tag = repo + ":recovery-" + image["image_id"].split(":")[1][:12]
        run([DOCKER, "tag", image["image_id"], SERVER + "/" + tag])
        run([DOCKER, "push", SERVER + "/" + tag])
        actual = run(["az", "acr", "repository", "show", "--name", REGISTRY, "--image", tag, "--query", "digest", "-o", "tsv"])
        if actual != image["platform_digest"]:
            raise RuntimeError("Restored platform manifest differs; do not deploy")
        images[name] = SERVER + "/" + repo + "@" + actual
    release["restored_images"] = images; save(release)
    kubeconfig = os.environ.get("KUBECONFIG")
    if not kubeconfig or Path(kubeconfig).name != "learningsteps-evolution.yaml":
        raise RuntimeError("Set the dedicated LearningSteps kubeconfig")
    run(["az", "aks", "get-credentials", "-g", "rg-learningsteps-evolution", "-n", "aks-learningsteps-evolution",
         "--subscription", SUB, "--file", kubeconfig, "--overwrite-existing", "--format", "exec"])
    run(["kubelogin", "convert-kubeconfig", "-l", "azurecli"])
    deadline = time.monotonic() + 300
    while True:
        try:
            nodes = json.loads(k("get", "nodes", "-o", "json"))["items"]
            if len(nodes) >= 2:break
        except RuntimeError:
            pass
        if time.monotonic() > deadline:raise RuntimeError("Cluster access not ready")
        time.sleep(15)
    k("apply", "-f", str(APP / "k8s-manifests/namespace.yaml"))
    os.environ["LEARNINGSTEPS_DIAGNOSTIC_IMAGE"] = images["api"]
    print("Configuring private database schema/role and restoring saved data...", flush=True)
    run(["python3", str(APP / "scripts/configure_cloud_database.py")])
    # A resumed bootstrap must verify restored data, never delete it to retry.
    data_mode = "verify-current" if release.get("database_restored") else "restore-empty"
    run(["python3", str(APP / "scripts/cloud_data_backup.py"), data_mode, "--manifest", str(ROOT / release["data_backup"])])
    release["database_restored"] = True; save(release)
    client_id = run(["az", "identity", "show", "-g", "rg-learningsteps-evolution", "-n", "id-learningsteps-api", "--query", "clientId", "-o", "tsv"])
    rendered = (APP / "k8s-manifests/workload-access.json").read_text().replace("__API_CLIENT_ID__", client_id)
    k("apply", "-f", "-", input=rendered)
    objects = [yaml.safe_load((APP / "k8s-manifests" / name).read_text()) for name in ("configmap.yaml", "deployment.yaml", "service.yaml", "hpa.yaml")]
    objects[1]["spec"]["template"]["spec"]["containers"][0]["image"] = images["api"]
    apply_objects(objects)
    k("rollout", "status", "deployment/learningsteps-api", "-n", "learningsteps", "--timeout=300s")
    print("Restoring encrypted certificate store before gateway startup...", flush=True)
    objects = list(yaml.safe_load_all((APP / "k8s-manifests/gateway/traefik.yaml").read_text()))
    deployment = next(o for o in objects if o["kind"] == "Deployment")
    deployment["spec"]["replicas"] = 0
    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = images["gateway"]
    config = next(o for o in objects if o["kind"] == "ConfigMap")
    full_dynamic = config["data"]["dynamic.yaml"]
    dynamic = yaml.safe_load(full_dynamic); dynamic["http"].pop("routers", None)
    config["data"]["dynamic.yaml"] = yaml.safe_dump(dynamic)
    apply_objects(objects)
    restorer = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "learningsteps-cert-restore", "namespace": "learningsteps"},
                "spec": {"restartPolicy": "Never", "activeDeadlineSeconds": 300, "automountServiceAccountToken": False,
                         "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001, "fsGroup": 10001, "seccompProfile": {"type": "RuntimeDefault"}},
                         "containers": [{"name": "restore", "image": images["gateway"], "command": ["/bin/sh", "-c", "sleep 290"],
                                         "securityContext": {"readOnlyRootFilesystem": True, "allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                                         "resources": {"requests": {"cpu": "25m", "memory": "32Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
                                         "volumeMounts": [{"name": "cert", "mountPath": "/data"}]}],
                         "volumes": [{"name": "cert", "persistentVolumeClaim": {"claimName": "learningsteps-https-data"}}]}}
    k("create", "-f", "-", input=json.dumps(restorer))
    try:
        k("wait", "--for=condition=Ready", "pod/learningsteps-cert-restore", "-n", "learningsteps", "--timeout=240s")
        info = json.loads((ROOT / release["data_backup"]).read_text())
        blob = (ROOT / cert_info["file"]).read_bytes()
        acme = AESGCM((ROOT / info["key_file"]).read_bytes()).decrypt(blob[8:20], blob[20:], b"learningsteps-acme-v1").decode()
        k("exec", "-i", "learningsteps-cert-restore", "-n", "learningsteps", "--", "/bin/sh", "-ec",
          "umask 077; cat > /data/acme.json; chmod 600 /data/acme.json", input=acme)
    finally:
        k("delete", "pod", "learningsteps-cert-restore", "-n", "learningsteps", "--timeout=90s")
    k("scale", "deployment/learningsteps-https", "-n", "learningsteps", "--replicas=1")
    k("rollout", "status", "deployment/learningsteps-https", "-n", "learningsteps", "--timeout=300s")
    print("Waiting for public HTTP convergence before enabling TLS router...", flush=True)
    deadline = time.monotonic() + 300; consecutive = 0
    while time.monotonic() < deadline:
        try:
            build_opener(NoRedirect()).open("http://" + HOST + "/docs", timeout=10)
        except HTTPError as e:
            consecutive = consecutive + 1 if e.code in (301, 302, 307, 308) else 0
        except OSError:
            consecutive = 0
        if consecutive >= 3:break
        time.sleep(10)
    if consecutive < 3:raise RuntimeError("Public HTTP not converged")
    config["data"]["dynamic.yaml"] = full_dynamic
    apply_objects([config])
    run(["python3", str(APP / "scripts/check_https_access.py"), "--timeout", "300"])
    client_id = run(["terraform", "-chdir=" + str(APP / "infra-terraform"), "output", "-raw", "github_actions_client_id"])
    run(["gh", "variable", "set", "AZURE_CLIENT_ID", "--repo", "CyberAlex91/learningsteps", "--body", client_id])
    release["bootstrap_verified_at"] = datetime.now(timezone.utc).isoformat(); save(release)
    print("PASS: images, database contents, workload identity configuration and trusted public HTTPS restored")
    print("GitHub public client-ID variable refreshed for recreated CI identity")


def infrastructure():
    directory = APP / "infra-terraform"
    state = set(run(["terraform", "-chdir=" + str(directory), "state", "list"]).splitlines())
    if "azurerm_resource_group.ai" not in state:
        print("Recreating Foundry resource group before optional soft-delete recovery...", flush=True)
        run(["terraform", "-chdir=" + str(directory), "apply", "-auto-approve", "-target=azurerm_resource_group.ai"], timeout=600)
    account_id = "/subscriptions/" + SUB + "/resourceGroups/rg-learningsteps-ai/providers/Microsoft.CognitiveServices/accounts/learningsteps-ai-alex-709d408c"
    if "azurerm_cognitive_account.foundry" not in state:
        existing = json.loads(run(["az", "resource", "list", "-g", "rg-learningsteps-ai", "--subscription", SUB, "-o", "json"]))
        live = any(r["id"].lower() == account_id.lower() for r in existing)
        if not live:
            deleted = json.loads(run(["az", "cognitiveservices", "account", "list-deleted", "--subscription", SUB, "-o", "json"]))
            matches = [r for r in deleted if r["name"] == "learningsteps-ai-alex-709d408c" and "/resourcegroups/rg-learningsteps-ai/" in r["id"].lower()]
            if matches:
                run(["az", "cognitiveservices", "account", "recover", "-g", "rg-learningsteps-ai", "-n", "learningsteps-ai-alex-709d408c", "-l", "germanywestcentral", "--subscription", SUB, "-o", "none"], timeout=600)
                live = True
        if live:run(["terraform", "-chdir=" + str(directory), "import", "azurerm_cognitive_account.foundry", account_id], timeout=600)
    print("Planning complete infrastructure recreation/resume...", flush=True)
    run(["terraform", "-chdir=" + str(directory), "plan", "-out=lifecycle-up.tfplan"], timeout=900)
    plan = json.loads(run(["terraform", "-chdir=" + str(directory), "show", "-json", "lifecycle-up.tfplan"]))
    if any("delete" in r["change"]["actions"] for r in plan.get("resource_changes", [])):
        raise RuntimeError("Unexpected deletion/replacement in restore plan; review before continuing")
    print("Applying non-destructive restore plan; AKS/database provisioning can take several minutes...", flush=True)
    run(["terraform", "-chdir=" + str(directory), "apply", "lifecycle-up.tfplan"], timeout=3600)
    print("PASS: complete infrastructure apply finished", flush=True)


def destroy_plan():
    release = json.loads(RELEASE.read_text())
    info = json.loads((ROOT / release["data_backup"]).read_text())
    if not info.get("isolated_restore_verified") or info["data_sha256"] != release["data_sha256"]:
        raise RuntimeError("Verified data restore required")
    for image in release["images"].values():
        if sha(ROOT / image["archive"]) != image["archive_sha256"]:raise RuntimeError("Image backup mismatch")
    if sha(ROOT / release["certificates"]["file"]) != release["certificates"]["sha256"]:
        raise RuntimeError("Certificate backup mismatch")
    # Literal lifecycle guards cannot be variables in Terraform. Save exact
    # source files and disable only these three known adoption guards.
    original = {}
    guard_backup = ROOT / ".state/evolution-guards.json"
    resumed = json.loads(guard_backup.read_text()) if guard_backup.exists() else None
    for rel, count in [("foundry.tf", 2), ("database.tf", 1)]:
        path = APP / "infra-terraform" / rel; text = path.read_text()
        if resumed is not None:
            if text.count("prevent_destroy = false") != count:
                raise RuntimeError("Unexpected lifecycle guards during resumed teardown")
            original[rel] = resumed[rel]
            continue
        if text.count("prevent_destroy = true") != count:
            raise RuntimeError("Unexpected lifecycle guard configuration")
        original[rel] = text
    guard_backup.write_text(json.dumps(original, indent=2))
    for rel, text in original.items():
        (APP / "infra-terraform" / rel).write_text(text.replace("prevent_destroy = true", "prevent_destroy = false"))
    print("Three adoption guards disabled only after verified data/image/certificate backups", flush=True)
    directory = APP / "infra-terraform"
    run(["terraform", "-chdir=" + str(directory), "plan", "-destroy", "-out=evolution-destroy.tfplan"], timeout=600)
    plan = json.loads(run(["terraform", "-chdir=" + str(directory), "show", "-json", "evolution-destroy.tfplan"]))
    deletions = []
    for resource in plan.get("resource_changes", []):
        actions = resource["change"]["actions"]
        if actions == ["no-op"]:continue
        if actions != ["delete"]:raise RuntimeError("Unexpected non-delete action in destroy plan")
        before = resource["change"]["before"]
        rid = before.get("id", "")
        allowed_groups = {"rg-learningsteps-ai", "rg-learningsteps-data", "rg-learningsteps-evolution", "rg-learningsteps-evolution-nodes"}
        allowed = "/resourcegroups/" in rid.lower() and rid.lower().split("/resourcegroups/", 1)[1].split("/", 1)[0] in allowed_groups
        allowed = allowed or resource["type"] == "azurerm_key_vault_secret" and rid.startswith("https://kv-lsteps-0ad5f630.vault.azure.net/secrets/")
        if not allowed:raise RuntimeError("Resource outside approved project groups in destroy plan")
        deletions.append({"address": resource["address"], "id": rid})
    summary = {"prepared_at": datetime.now(timezone.utc).isoformat(), "deletions": deletions,
               "count": len(deletions), "plan_sha256": sha(directory / "evolution-destroy.tfplan"),
               "data_backup": release["data_backup"], "remote_state_storage_deleted": False}
    (ROOT / "artifacts/azure/evolution-destroy-plan.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("PASS: reviewed destroy plan contains only " + str(len(deletions)) + " project resources; state storage excluded")


def restore_guards():
    path = ROOT / ".state/evolution-guards.json"
    original = json.loads(path.read_text())
    for rel, text in original.items():
        current = APP / "infra-terraform" / rel
        content = current.read_text()
        if content.count("prevent_destroy = true") == text.count("prevent_destroy = true") and "prevent_destroy = false" not in content:
            continue
        if content.count("prevent_destroy = false") != text.count("prevent_destroy = true"):
            raise RuntimeError("Unexpected lifecycle guards; restore manually")
        # Preserve reviewed capacity corrections made during actual rebuild.
        current.write_text(content.replace("prevent_destroy = false", "prevent_destroy = true"))
    path.unlink()
    print("PASS: original lifecycle guards restored")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "bootstrap", "infrastructure", "plan-destroy", "restore-guards"])
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if run(["az", "account", "show", "--query", "id", "-o", "tsv"]) != SUB:
        raise RuntimeError("Wrong subscription")
    if args.mode == "prepare":
        if args.backup is None:raise RuntimeError("Specify tested data backup")
        prepare(args.backup.resolve())
    elif args.mode == "bootstrap":
        bootstrap(json.loads(RELEASE.read_text()))
    elif args.mode == "infrastructure":
        infrastructure()
    elif args.mode == "plan-destroy":
        destroy_plan()
    else:
        restore_guards()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("STOP: " + (str(error) if type(error) is RuntimeError else type(error).__name__))
        raise SystemExit(1) from None
