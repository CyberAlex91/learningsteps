# Zweck: Prüft den tatsächlich wiederaufgebauten Cluster, unveränderte Daten, HTTPS und KI und speichert nur sichere Abschlussmetadaten.
"""Run in WSL after bootstrap and restoring lifecycle guards; never creates notes."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"


def run(args, *, input=None, timeout=600):
    result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Acceptance command failed: " + Path(args[0]).name + "; raw output withheld")
    return result.stdout


def main():
    release = json.loads((ROOT / ".state/evolution-release.json").read_text())
    if not release.get("bootstrap_verified_at"):
        raise RuntimeError("Successful bootstrap required")
    destroyed = json.loads((ROOT / "artifacts/azure/terraform-destroy-check.json").read_text())
    expected_count = destroyed["destroyed_resources"]
    if destroyed["managed_resources_remaining"] != 0 or expected_count <= 0:
        raise RuntimeError("Actual complete destroy evidence required")
    for helper, extra in [
        ("cloud_data_backup.py", ["verify-current", "--manifest", str(ROOT / release["data_backup"])]),
        ("check_api_rollout.py", []),
        ("check_workload_access.py", []),
        ("check_https_access.py", ["--timeout", "180"]),
    ]:
        print("Checking " + helper + "...", flush=True)
        print(run(["python3", str(APP / "scripts" / helper), *extra]), flush=True)
    before = json.loads((ROOT / "artifacts/azure/before-infrastructure-recovery.json").read_text())
    namespace = json.loads(run(["kubectl", "get", "namespace", "learningsteps", "-o", "json"]))
    cluster = json.loads(run(["az", "aks", "show", "-g", "rg-learningsteps-evolution", "-n", "aks-learningsteps-evolution",
                             "--query", "{fqdn:fqdn,issuer:oidcIssuerProfile.issuerUrl}", "-o", "json"]))
    if namespace["metadata"]["uid"] == before["namespace_uid"] or cluster["issuer"] == before["oidc"]["issuerUrl"]:
        raise RuntimeError("Expected a genuinely new cluster and namespace")
    print("Checking actual Foundry inference from the restored API...", flush=True)
    source = (APP / "tests/check_foundry_connection.py").read_text()
    inference = json.loads(run(["kubectl", "exec", "-i", "deployment/learningsteps-api", "-n", "learningsteps", "-c", "api", "--",
                               "python", "-c", "import sys;__file__='/app/tests/check_foundry_connection.py';exec(compile(sys.stdin.read(),__file__,'exec'))"], input=source))
    if not inference.get("success") or inference.get("credential") != "workload_identity":
        raise RuntimeError("Actual keyless workload inference required")
    (ROOT / "artifacts/azure/foundry-after-recovery-check.json").write_text(json.dumps(inference, ensure_ascii=False, indent=2) + "\n")
    # detailed-exitcode: 0=no changes, 2=changes. Capture output to avoid exposing state.
    run(["terraform", "-chdir=" + str(APP / "infra-terraform"), "plan", "-detailed-exitcode", "-no-color"], timeout=900)
    state = run(["terraform", "-chdir=" + str(APP / "infra-terraform"), "state", "list"]).splitlines()
    if len(state) != expected_count:
        raise RuntimeError("Expected all previously managed project resources")
    snapshot = json.loads(run(["terraform", "-chdir=" + str(APP / "infra-terraform"), "show", "-json"]))
    if any(bool(resource["values"].get("value")) for resource in snapshot["values"]["root_module"]["resources"]
           if resource["type"] == "azurerm_key_vault_secret"):
        raise RuntimeError("Regular secret values must be empty in current state")
    current = json.loads((ROOT / "artifacts/azure/data-current-check.json").read_text())
    restored = json.loads((ROOT / "artifacts/azure/data-restore-empty-check.json").read_text())
    if current["data_sha256"] != release["data_sha256"] or restored["data_sha256"] != release["data_sha256"]:
        raise RuntimeError("Restored data must exactly match the saved backup")
    lifecycle = ROOT / ".state/lifecycle.json"
    backend_recreated = lifecycle.exists() and json.loads(lifecycle.read_text()).get("phase") == "up"
    evidence = {
        "passed": True, "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": str(expected_count) + " Ressourcen vollständig abgebaut und wiederhergestellt; " + str(current["count"]) + " Notizen mit identischem Datenhash restauriert. HTTPS, zwei API-Replikate, eingeschränkter Datenbankzugriff und echte KI per Workload Identity erneut geprüft. Terraform: keine Änderungen.",
        "destroyed_resources": expected_count, "managed_resources_after_rebuild": len(state),
        "restored_notes": current["count"], "data_sha256": current["data_sha256"],
        "new_namespace_uid": namespace["metadata"]["uid"], "new_cluster": cluster,
        "trusted_https": True, "workload_identity_inference": True,
        "terraform_no_changes": True, "remote_state_storage_preserved": not backend_recreated,
        "remote_state_backend_recreated": backend_recreated,
        "current_state_regular_secret_values_empty": True,
        "private_backup_material_included": False,
    }
    (ROOT / "artifacts/azure/evolution-recovery-final.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("PASS: actual complete infrastructure and data recovery accepted")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("STOP: " + (str(error) if type(error) is RuntimeError else type(error).__name__))
        raise SystemExit(1) from None
