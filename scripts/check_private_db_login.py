"""Read-only AKS-to-PostgreSQL acceptance, with a memory-only vault password."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


POD = "learningsteps-db-login-check"
NAMESPACE = "learningsteps"
HOST = "psql-learningsteps-alex-0ad5f630.postgres.database.azure.com"
IMAGE = "sha256:de2ed68b2b5d9b6a253d08155d8ccd307d532fa489b0bab7a755b186476de2df"

# Only this code (without the password) appears in kubectl's process arguments.
# JSON credentials are transmitted through the exec stream's standard input.
REMOTE_CHECK = r'''
import asyncio
import json
import ssl
import sys
import asyncpg

async def main():
    config = json.load(sys.stdin)
    tls = ssl.create_default_context()
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = await asyncpg.connect(
        host=config["host"], database="learningsteps", user="learningsteps_admin",
        password=config["password"], ssl=tls, timeout=15,
        server_settings={"application_name": "learningsteps-readonly-acceptance"},
    )
    try:
        row = await connection.fetchrow(
            "SELECT current_database() AS database, current_user AS username, "
            "s.ssl, s.version AS tls_version FROM pg_stat_ssl s "
            "WHERE s.pid = pg_backend_pid()"
        )
        print(json.dumps(dict(row)))
    finally:
        await connection.close()

try:
    asyncio.run(main())
except Exception as error:
    print("Database acceptance failed: " + type(error).__name__, file=sys.stderr)
    sys.exit(1)
'''


def capture(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=240, **kwargs)
    if result.returncode:
        # Never print subprocess args/stdin, vault values, or raw SDK/CLI errors.
        raise RuntimeError("Command failed during " + arguments[0] + " operation")
    return result.stdout.strip()


def main():
    app = Path(__file__).resolve().parents[1]
    context = capture(["kubectl", "config", "current-context"])
    if context != "aks-learningsteps-evolution":
        raise RuntimeError("Expected the LearningSteps AKS context")
    existing = capture([
        "kubectl", "get", "pod", POD, "-n", NAMESPACE,
        "--ignore-not-found", "-o", "name",
    ])
    if existing:
        raise RuntimeError("Diagnostic pod already exists; review it before retrying")

    created = False
    try:
        capture([
            "kubectl", "apply", "-f",
            str(app / "k8s-manifests" / "diagnostics" / "db-login-check.yaml"),
        ])
        created = True
        capture([
            "kubectl", "wait", "--for=condition=Ready", "pod/" + POD,
            "-n", NAMESPACE, "--timeout=180s",
        ])
        print("PASS: isolated diagnostic pod Ready", flush=True)

        password = capture([
            "az", "keyvault", "secret", "show", "--vault-name", "kv-lsteps-0ad5f630",
            "--name", "postgres-admin-password", "--subscription", "Alexander Plank - Sub",
            "--query", "value", "--output", "tsv", "--only-show-errors",
        ])
        if not password:
            raise RuntimeError("Vault returned an empty credential")
        output = capture(
            ["kubectl", "exec", "-i", POD, "-n", NAMESPACE, "--", "python", "-c", REMOTE_CHECK],
            input=json.dumps({"host": HOST, "password": password}),
        )
        del password
        result = json.loads(output)
        if (result.get("database") != "learningsteps"
                or result.get("username") != "learningsteps_admin"
                or result.get("ssl") is not True
                or result.get("tls_version") not in ("TLSv1.2", "TLSv1.3")):
            raise RuntimeError("Unexpected database, login or TLS result")
        # Only an explicit allowlist of non-secret metadata is written or printed.
        evidence = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "host": HOST, "database": result["database"], "username": result["username"],
            "ssl": result["ssl"], "tls_version": result["tls_version"],
            "image_digest": IMAGE, "sql_performed": "read-only connection metadata SELECT",
            "password_printed_or_saved": False,
        }
        target = app.parent / "artifacts" / "azure" / "private-db-login-check.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("PASS: admin login to learningsteps through verified TLS")
        print("PASS: read-only connection metadata returned; protocol=" + result["tls_version"])
        print("Evidence: artifacts/azure/private-db-login-check.json")
    finally:
        if created:
            capture(["kubectl", "delete", "pod", POD, "-n", NAMESPACE, "--wait=true", "--timeout=90s"])
            print("Diagnostic pod removed", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Print our safe fixed messages, never raw unexpected exception strings.
        message = str(error) if type(error) is RuntimeError else type(error).__name__
        print("STOP: " + message, file=sys.stderr)
        sys.exit(1)
