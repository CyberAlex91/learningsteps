"""Configure API SA/CSI and verify workload access without host-side secrets.

Run from LearningSteps in WSL. Retains the reusable ServiceAccount and
SecretProviderClass. Creates/deletes only its named diagnostic pod. No note writes.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import UUID

from check_private_db_login import capture

POD = "learningsteps-workload-access-check"
NAMESPACE = "learningsteps"
SUBSCRIPTION = "0ad5f630-c506-401a-93fa-36b0fe313829"
TENANT = "c0531484-50fa-4ff2-97df-b1f2d4810603"

REMOTE_CHECK = r'''
import json
import logging
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import psycopg2
from azure.identity import WorkloadIdentityCredential

logging.getLogger("azure").setLevel(logging.CRITICAL)
stage = "mounted-secret"
try:
    secret = Path("/mnt/secrets-store/database-url").read_text().strip()
    if not secret:
        raise RuntimeError()
    stage = "database-login"
    with psycopg2.connect(secret, connect_timeout=15,
                          application_name="learningsteps-workload-acceptance") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SELECT current_user, current_database(), ssl, version "
                           "FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
            username, database, ssl, tls = cursor.fetchone()
            if username != "learningsteps_app" or database != "learningsteps" or not ssl:
                raise RuntimeError()
            if tls not in ("TLSv1.2", "TLSv1.3"):
                raise RuntimeError()
            cursor.execute("SELECT count(*) FROM public.entries")
            count = cursor.fetchone()[0]
    del secret
    stage = "workload-token"
    # No fallback to developer CLI or node managed identity.
    with WorkloadIdentityCredential() as credential:
        token = credential.get_token("https://vault.azure.net/.default")
        stage = "deny-admin-secret"
        request = Request(
            "https://kv-lsteps-0ad5f630.vault.azure.net/secrets/postgres-admin-password?api-version=7.4",
            headers={"Authorization": "Bearer " + token.token},
        )
        try:
            with urlopen(request, timeout=20) as response:
                # Never read or print an unexpectedly permitted admin secret.
                raise RuntimeError()
        except HTTPError as error:
            body = json.loads(error.read(65536))
            detail = body.get("error", {})
            inner = detail.get("innererror", {}).get("code")
            if error.code != 403 or inner != "ForbiddenByRbac":
                raise RuntimeError()
    print(json.dumps({"ok": True, "mounted_secret": True,
                      "database_user": username, "database": database,
                      "tls_version": tls, "entry_count": count,
                      "admin_secret_denied_by_rbac": True,
                      "credential_type": "WorkloadIdentityCredential"}))
except Exception as error:
    print(json.dumps({"ok": False, "stage": stage,
                      "error_type": type(error).__name__}))
    raise SystemExit(1)
'''


def main():
    app = Path(__file__).resolve().parents[1]
    if capture(["kubectl", "config", "current-context"]) != "aks-learningsteps-evolution":
        raise RuntimeError("Expected LearningSteps AKS context")
    account = json.loads(capture(["az", "account", "show", "-o", "json"]))
    if account["id"] != SUBSCRIPTION or account["tenantId"] != TENANT:
        raise RuntimeError("Expected LearningSteps subscription and tenant")
    if capture(["kubectl", "get", "pod", POD, "-n", NAMESPACE,
                "--ignore-not-found", "-o", "name"]):
        raise RuntimeError("Diagnostic pod exists; review before retrying")
    client_id = str(UUID(capture([
        "az", "identity", "show", "--subscription", SUBSCRIPTION,
        "--resource-group", "rg-learningsteps-evolution", "--name", "id-learningsteps-api",
        "--query", "clientId", "-o", "tsv",
    ])))
    template = app / "k8s-manifests" / "workload-access.json"
    rendered = template.read_text(encoding="utf-8").replace("__API_CLIENT_ID__", client_id)
    json.loads(rendered)
    capture(["kubectl", "apply", "-f", "-"], input=rendered)
    print("PASS: API ServiceAccount and CSI configuration applied (public IDs only)", flush=True)
    created = False
    try:
        # Create refuses overwriting a pod created concurrently by another run.
        capture(["kubectl", "create", "-f", str(
            app / "k8s-manifests" / "diagnostics" / "workload-access-check.yaml")])
        created = True
        capture(["kubectl", "wait", "--for=condition=Ready", "pod/" + POD,
                 "-n", NAMESPACE, "--timeout=180s"])
        print("PASS: pod Ready with Workload Identity and mounted vault secret", flush=True)
        execution = subprocess.run(
            ["kubectl", "exec", POD, "-n", NAMESPACE,
             "--", "python", "-c", REMOTE_CHECK],
            capture_output=True, text=True, timeout=150,
        )
        # Never print raw stdout/stderr, exception messages or request headers.
        # Only the controlled stage and exception class can leave a failed pod.
        try:
            result = json.loads(execution.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("Remote check returned no structured result; transport/runtime error") from None
        if execution.returncode or result.get("ok") is not True:
            stage = result.get("stage", "unknown")
            error_type = result.get("error_type", "UnknownError")
            stages = {"mounted-secret", "database-login", "workload-token", "deny-admin-secret"}
            if stage not in stages or not isinstance(error_type, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", error_type):
                raise RuntimeError("Remote check failed; invalid diagnostic metadata")
            raise RuntimeError(f"Remote check failed at {stage} ({error_type})")
        if result.get("ok") is not True or result.get("admin_secret_denied_by_rbac") is not True:
            raise RuntimeError("Unexpected workload test result")
        fields = ("mounted_secret", "database_user", "database", "tls_version",
                  "entry_count", "admin_secret_denied_by_rbac", "credential_type")
        evidence = {key: result[key] for key in fields}
        evidence["checked_at"] = datetime.now(timezone.utc).isoformat()
        target = app.parent / "artifacts" / "azure" / "workload-access-check.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("PASS: mounted connection URL used for restricted app login and read-only SQL")
        print("PASS: verified database TLS " + result["tls_version"])
        print("PASS: admin secret explicitly denied by Key Vault RBAC")
        print("Evidence: artifacts/azure/workload-access-check.json")
    finally:
        if created:
            capture(["kubectl", "delete", "pod", POD, "-n", NAMESPACE,
                     "--wait=true", "--timeout=90s"])
            print("Diagnostic pod removed; reusable SA/CSI configuration retained", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error) if type(error) is RuntimeError else type(error).__name__
        print("STOP: " + message + "; secret values/raw errors withheld.", file=sys.stderr)
        sys.exit(1)
