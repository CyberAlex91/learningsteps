# Zweck: Richtet Cloud-Datenbankschema und eingeschränkte App-Rolle ohne Notizlöschung ein.
"""Initialize only the dedicated cloud DB; credentials stay in memory/stdin."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from check_private_db_login import HOST, IMAGE, NAMESPACE, POD, capture, create_diagnostic_pod


REMOTE_CONFIGURE = r'''
import json
import sys
import psycopg2
from psycopg2 import sql, extensions

stage = "input"
try:
    config = json.load(sys.stdin)
    def connect(user, password):
        return psycopg2.connect(
            host=config["host"], dbname="learningsteps", user=user, password=password,
            sslmode="verify-full", sslrootcert="/etc/ssl/certs/ca-certificates.crt",
            connect_timeout=15, application_name="learningsteps-schema-bootstrap",
        )

    stage = "admin connection"
    admin = connect("learningsteps_admin", config["admin_password"])
    try:
        with admin:
            with admin.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '10s'")
                cursor.execute("SET LOCAL statement_timeout = '30s'")
                cursor.execute("SELECT pg_advisory_xact_lock(817401)")
                stage = "logging preflight"
                cursor.execute("SHOW log_statement")
                if cursor.fetchone()[0] != "none":
                    raise RuntimeError("Statement logging enabled")
                cursor.execute("SHOW log_min_duration_statement")
                if cursor.fetchone()[0] != "-1":
                    raise RuntimeError("Duration logging enabled")
                cursor.execute("SHOW log_min_duration_sample")
                if cursor.fetchone()[0] != "-1":
                    raise RuntimeError("Sample logging enabled")
                cursor.execute("SELECT current_setting('pgaudit.log', true)")
                if cursor.fetchone()[0] not in (None, "", "none"):
                    raise RuntimeError("Audit statement logging enabled")

                stage = "existing schema check"
                cursor.execute("SELECT to_regclass('public.entries')")
                exists = cursor.fetchone()[0] is not None
                before = 0
                if exists:
                    cursor.execute("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='public.entries'::regclass")
                    if cursor.fetchone()[0] != "learningsteps_admin":
                        raise RuntimeError("Unexpected table owner")
                    cursor.execute("SELECT count(*) FROM public.entries")
                    before = cursor.fetchone()[0]

                stage = "schema"
                cursor.execute(config["schema_sql"])
                stage = "application role"
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='learningsteps_app'")
                if cursor.fetchone() is None:
                    cursor.execute("CREATE ROLE learningsteps_app LOGIN")
                cursor.execute(
                    "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls "
                    "FROM pg_roles WHERE rolname='learningsteps_app'"
                )
                if cursor.fetchone()[0]:
                    raise RuntimeError("Existing app role has elevated privileges")
                cursor.execute(
                    "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member "
                    "WHERE r.rolname='learningsteps_app'"
                )
                if cursor.fetchone()[0]:
                    raise RuntimeError("Unexpected app role memberships")
                # libpq creates a SCRAM verifier locally, rather than placing a
                # cleartext password in an ALTER ROLE SQL statement.
                verifier = extensions.encrypt_password(
                    config["app_password"], "learningsteps_app", admin,
                    algorithm="scram-sha-256",
                )
                cursor.execute(sql.SQL("ALTER ROLE learningsteps_app LOGIN CONNECTION LIMIT 20 PASSWORD {}").format(sql.Literal(verifier)))
                stage = "grants"
                cursor.execute(config["access_sql"])
                cursor.execute("SELECT count(*) FROM public.entries")
                after = cursor.fetchone()[0]
                if before != after:
                    raise RuntimeError("Unexpected entry count change")
    finally:
        admin.close()

    stage = "application login"
    app = connect("learningsteps_app", config["app_password"])
    try:
        with app:
            with app.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM public.entries")
                app_count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT has_table_privilege(current_user,'public.entries','SELECT') "
                    "AND has_table_privilege(current_user,'public.entries','INSERT') "
                    "AND has_table_privilege(current_user,'public.entries','UPDATE') "
                    "AND has_table_privilege(current_user,'public.entries','DELETE'), "
                    "has_schema_privilege(current_user,'public','CREATE')"
                )
                dml, ddl = cursor.fetchone()
                if not dml or ddl:
                    raise RuntimeError("Unexpected app privileges")
                cursor.execute("SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
                encrypted, protocol = cursor.fetchone()
                if not encrypted:
                    raise RuntimeError("Expected TLS")
                stage = "DDL rejection"
                cursor.execute("SAVEPOINT deny_ddl")
                try:
                    cursor.execute("CREATE TABLE public.learningsteps_forbidden_probe (id integer)")
                except psycopg2.errors.InsufficientPrivilege:
                    cursor.execute("ROLLBACK TO SAVEPOINT deny_ddl")
                else:
                    cursor.execute("ROLLBACK TO SAVEPOINT deny_ddl")
                    raise RuntimeError("App unexpectedly created a table")
    finally:
        app.close()
    print(json.dumps({
        "ok": True, "entries_before": before, "entries_after": after,
        "app_read_count": app_count, "dml_granted": dml,
        "schema_create_denied": True, "tls_version": protocol,
    }))
except Exception as error:
    # No raw database exceptions, SQL, credentials or verifiers in output.
    print(json.dumps({"ok": False, "stage": stage, "error_type": type(error).__name__}))
'''


def main():
    app = Path(__file__).resolve().parents[1]
    if capture(["kubectl", "config", "current-context"]) != "aks-learningsteps-evolution":
        raise RuntimeError("Expected LearningSteps AKS context")
    if capture(["kubectl", "get", "pod", POD, "-n", NAMESPACE, "--ignore-not-found", "-o", "name"]):
        raise RuntimeError("Diagnostic pod already exists; review before retrying")
    # Reuse the existing schema, removing only its psql display meta-command.
    lines = (app / "database_setup.sql").read_text(encoding="utf-8-sig").splitlines()
    if any(line.lstrip().startswith("\\") and line.strip() != "\\d entries;" for line in lines):
        raise RuntimeError("Unexpected psql meta-command in schema")
    schema = "\n".join(line for line in lines if not line.lstrip().startswith("\\"))
    access_sql = (app / "database" / "cloud_access.sql").read_text(encoding="utf-8")
    created = False
    try:
        create_diagnostic_pod()
        created = True
        capture(["kubectl", "wait", "--for=condition=Ready", "pod/" + POD, "-n", NAMESPACE, "--timeout=180s"])
        print("PASS: isolated setup pod Ready", flush=True)
        config = {"host": HOST, "schema_sql": schema, "access_sql": access_sql}
        for role in ("admin", "app"):
            config[role + "_password"] = capture([
                "az", "keyvault", "secret", "show", "--vault-name", "kv-lsteps-0ad5f630",
                "--name", "postgres-" + role + "-password", "--subscription", "Alexander Plank - Sub",
                "--query", "value", "--output", "tsv", "--only-show-errors",
            ])
            if not config[role + "_password"]:
                raise RuntimeError("Missing vault credential")
        output = capture(["kubectl", "exec", "-i", POD, "-n", NAMESPACE, "--", "python", "-c", REMOTE_CONFIGURE], input=json.dumps(config))
        config.clear()
        result = json.loads(output)
        if not result.get("ok"):
            # Only stage and exception class from our controlled code, no error text.
            raise RuntimeError("Setup stopped at " + str(result.get("stage")) + ": " + str(result.get("error_type")))
        evidence = {key: result[key] for key in (
            "ok", "entries_before", "entries_after", "app_read_count", "dml_granted",
            "schema_create_denied", "tls_version",
        )}
        evidence.update(checked_at=datetime.now(timezone.utc).isoformat(), image_digest=IMAGE)
        target = app.parent / "artifacts" / "azure" / "cloud-database-schema-check.json"
        target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("PASS: schema and restricted app role configured")
        print("PASS: entry count unchanged: " + str(result["entries_after"]))
        print("PASS: app password login and read access over " + result["tls_version"])
        print("PASS: table data rights granted, CREATE TABLE rejected")
        print("Evidence: artifacts/azure/cloud-database-schema-check.json")
    finally:
        if created:
            capture(["kubectl", "delete", "pod", POD, "-n", NAMESPACE, "--wait=true", "--timeout=90s"])
            print("Setup pod removed", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error) if type(error) is RuntimeError else type(error).__name__
        print("STOP: " + message, file=sys.stderr)
        sys.exit(1)
