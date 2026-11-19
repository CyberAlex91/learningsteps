# Zweck: Sichert alle Anwendungsdaten verschlüsselt und prüft beziehungsweise restauriert sie ohne Überschreiben vorhandener Einträge.
"""Logical entries backup; schema/roles are recreated separately from source."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from check_private_db_login import capture, HOST

ROOT = Path(__file__).resolve().parents[2]
AAD = b"learningsteps-entries-v1"
REMOTE = r'''
import hashlib,json,sys
import psycopg2
from psycopg2 import sql
c=json.load(sys.stdin)
def connect(database):
    conn=psycopg2.connect(host=c['host'],dbname=database,user='learningsteps_admin',
        password=c['password'],sslmode='verify-full',sslrootcert='/etc/ssl/certs/ca-certificates.crt',
        connect_timeout=15,application_name='learningsteps-data-recovery')
    with conn.cursor() as cur:
        for name,expected in [('log_statement','none'),('log_min_duration_statement','-1'),('log_min_duration_sample','-1')]:
            cur.execute(sql.SQL('SHOW {}').format(sql.Identifier(name)))
            if cur.fetchone()[0]!=expected:raise RuntimeError('SQL statement logging enabled')
        cur.execute("SELECT current_setting('pgaudit.log', true)")
        if cur.fetchone()[0] not in (None,'','none'):raise RuntimeError('SQL audit logging enabled')
    conn.rollback()
    return conn
def rows(conn):
    with conn.cursor() as cur:
        cur.execute("SET LOCAL TIME ZONE 'UTC'")
        cur.execute('SELECT row_to_json(e) FROM public.entries e ORDER BY id')
        return [r[0] for r in cur.fetchall()]
def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
stage='connect'; temporary=None; control=None
try:
    if c['mode']=='backup':
        conn=connect('learningsteps')
        try:
            conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
            with conn,conn.cursor() as cur:
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                if [r[0] for r in cur.fetchall()]!=['entries']:raise RuntimeError('Unrecognized application tables')
                data=rows(conn)
            print(json.dumps({'ok':True,'rows':data,'sha256':fingerprint(data)},ensure_ascii=False))
        finally:conn.close()
    else:
        stage='create isolated database'
        database='learningsteps'
        if c['mode']=='check':
            temporary='ls_restore_'+c['nonce']
            control=connect('postgres');control.autocommit=True
            with control.cursor() as cur:
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(temporary)))
            database=temporary
        conn=connect(database)
        try:
            with conn,conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='30s'")
                cur.execute("SET LOCAL lock_timeout='10s'")
                cur.execute(c['schema'])
                cur.execute('LOCK TABLE public.entries IN ACCESS EXCLUSIVE MODE')
                cur.execute('SELECT count(*) FROM public.entries')
                stage='empty target guard'
                if cur.fetchone()[0]!=0:raise RuntimeError('Restore target not empty')
                stage='insert saved entries'
                for r in c['rows']:
                    cur.execute('INSERT INTO public.entries (id,data,created_at,updated_at,owner_tenant_id,owner_object_id) VALUES (%s,%s,%s,%s,%s,%s)',
                        (r['id'],json.dumps(r['data']),r['created_at'],r['updated_at'],r['owner_tenant_id'],r['owner_object_id']))
                actual=rows(conn)
                if fingerprint(actual)!=c['sha256']:raise RuntimeError('Content verification failed')
            print(json.dumps({'ok':True,'count':len(actual),'sha256':fingerprint(actual),'isolated':c['mode']=='check'}))
        finally:conn.close()
except Exception as e:
    print(json.dumps({'ok':False,'stage':stage,'error_type':type(e).__name__,
                     'code':'target-not-empty' if str(e)=='Restore target not empty' else 'operation-failed'}));sys.exit(1)
finally:
    if control is not None:
        try:
            with control.cursor() as cur:cur.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(temporary)))
        finally:control.close()
'''


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def diagnostic():
    image = os.environ.get("LEARNINGSTEPS_DIAGNOSTIC_IMAGE")
    if not image:
        deployment = json.loads(capture(["kubectl", "get", "deployment", "learningsteps-api", "-n", "learningsteps", "-o", "json"]))
        image = next(c["image"] for c in deployment["spec"]["template"]["spec"]["containers"] if c["name"] == "api")
    if not re.fullmatch(r"acrlearningstepsalex0ad5f630\.azurecr\.io/learningsteps-api@sha256:[a-f0-9]{64}", image):
        raise RuntimeError("Expected immutable project API image")
    name = "learningsteps-backup-" + uuid4().hex[:8]
    manifest = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": name, "namespace": "learningsteps"},
                "spec": {"restartPolicy": "Never", "activeDeadlineSeconds": 600, "automountServiceAccountToken": False,
                         "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "seccompProfile": {"type": "RuntimeDefault"}},
                         "containers": [{"name": "check", "image": image, "command": ["python", "-c", "import time; time.sleep(590)"],
                                         "securityContext": {"readOnlyRootFilesystem": True, "allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                                         "resources": {"requests": {"cpu": "50m", "memory": "32Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}}}]}}
    capture(["kubectl", "create", "-f", "-"], input=json.dumps(manifest))
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["backup", "check", "restore-empty", "verify-current"])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if capture(["kubectl", "config", "current-context"]) != "aks-learningsteps-evolution":
        raise RuntimeError("Wrong Kubernetes context")
    if capture(["az", "account", "show", "--query", "id", "-o", "tsv"]) != "0ad5f630-c506-401a-93fa-36b0fe313829":
        raise RuntimeError("Wrong Azure subscription")
    config = {"mode": "check" if args.mode == "check" else "backup" if args.mode in ("backup", "verify-current") else "restore",
              "host": HOST, "nonce": uuid4().hex}
    manifest_path = args.manifest
    if args.mode != "backup":
        if manifest_path is None:
            raise RuntimeError("Specify the exact backup manifest")
        info = json.loads(manifest_path.read_text())
        if args.mode == "restore-empty" and info.get("isolated_restore_verified") is not True:
            raise RuntimeError("A verified isolated restore is required first")
        encrypted = ROOT / info["encrypted_file"]
        key_file = ROOT / info["key_file"]
        if not encrypted.resolve().is_relative_to(ROOT / "artifacts/backups") or not key_file.resolve().is_relative_to(ROOT / ".secrets/backups"):
            raise RuntimeError("Backup paths outside expected directories")
        blob = encrypted.read_bytes()
        if hashlib.sha256(blob).hexdigest() != info["encrypted_sha256"] or not blob.startswith(b"LSBACKUP1"):
            raise RuntimeError("Encrypted backup mismatch")
        data = json.loads(AESGCM(key_file.read_bytes()).decrypt(blob[9:21], blob[21:], AAD))
        if digest(data) != info["data_sha256"]:
            raise RuntimeError("Decrypted content mismatch")
        config.update(rows=data, sha256=info["data_sha256"])
        schema = (ROOT / "app/database_setup.sql").read_text()
        config["schema"] = "\n".join(line for line in schema.splitlines() if not line.lstrip().startswith("\\"))
    pod = diagnostic()
    try:
        capture(["kubectl", "wait", "--for=condition=Ready", "pod/" + pod, "-n", "learningsteps", "--timeout=180s"])
        config["password"] = capture(["az", "keyvault", "secret", "show", "--vault-name", "kv-lsteps-0ad5f630", "--name", "postgres-admin-password", "--subscription", "Alexander Plank - Sub", "--query", "value", "-o", "tsv", "--only-show-errors"])
        execution = subprocess.run(["kubectl", "exec", "-i", pod, "-n", "learningsteps", "--", "python", "-c", REMOTE], input=json.dumps(config), capture_output=True, text=True, timeout=240)
        result = json.loads(execution.stdout)
        config.clear()
        if result.get("code") == "target-not-empty":
            raise RuntimeError("Restore target not empty; existing records preserved")
        if execution.returncode or result.get("ok") is not True:
            raise RuntimeError("Remote backup/restore did not pass")
        if args.mode == "backup":
            data = result.pop("rows")
            if digest(data) != result["sha256"]:
                raise RuntimeError("Export digest mismatch")
            name = "evolution-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
            backup_dir = ROOT / "artifacts/backups"; backup_dir.mkdir(parents=True, exist_ok=True)
            keys = ROOT / ".secrets/backups"; keys.mkdir(parents=True, exist_ok=True)
            key = AESGCM.generate_key(bit_length=256); nonce = os.urandom(12)
            blob = b"LSBACKUP1" + nonce + AESGCM(key).encrypt(nonce, json.dumps(data, ensure_ascii=False).encode(), AAD)
            key_file = keys / (name + ".key"); encrypted = backup_dir / (name + ".enc")
            with key_file.open("xb") as f:f.write(key)
            key_file.chmod(0o600)
            with encrypted.open("xb") as f:f.write(blob)
            assert json.loads(AESGCM(key_file.read_bytes()).decrypt(blob[9:21], blob[21:], AAD)) == data
            info = {"created_at": datetime.now(timezone.utc).isoformat(), "scope": "all rows of sole public application table entries; schema/roles from source",
                    "count": len(data), "data_sha256": digest(data), "encrypted_sha256": hashlib.sha256(blob).hexdigest(),
                    "encrypted_file": encrypted.relative_to(ROOT).as_posix(), "key_file": key_file.relative_to(ROOT).as_posix(), "isolated_restore_verified": False}
            manifest_path = backup_dir / (name + ".json")
            manifest_path.write_text(json.dumps(info, indent=2) + "\n")
        elif args.mode == "verify-current":
            if digest(result["rows"]) != info["data_sha256"]:
                raise RuntimeError("Live contents differ from verified backup; do not destroy")
            evidence = {"mode": args.mode, "count": len(result["rows"]), "data_sha256": info["data_sha256"],
                        "verified_at": datetime.now(timezone.utc).isoformat(), "database_modified": False}
            (ROOT / "artifacts/azure/data-current-check.json").write_text(json.dumps(evidence, indent=2) + "\n")
        else:
            if result["sha256"] != info["data_sha256"] or result["count"] != info["count"]:
                raise RuntimeError("Restored data differs")
            if args.mode == "check":
                info["isolated_restore_verified"] = True
                info["isolated_restore_verified_at"] = datetime.now(timezone.utc).isoformat()
                manifest_path.write_text(json.dumps(info, indent=2) + "\n")
            evidence = {"mode": args.mode, "count": result["count"], "data_sha256": result["sha256"], "verified_at": datetime.now(timezone.utc).isoformat(), "manifest": str(manifest_path.relative_to(ROOT)), "original_database_modified": args.mode == "restore-empty"}
            (ROOT / "artifacts/azure" / ("data-" + args.mode + "-check.json")).write_text(json.dumps(evidence, indent=2) + "\n")
        print("PASS: " + args.mode + "; records=" + str(info["count"]) + "; full data SHA-256 verified")
        print("Manifest: " + str(manifest_path))
    finally:
        capture(["kubectl", "delete", "pod", pod, "-n", "learningsteps", "--timeout=90s"])
        print("Temporary diagnostic pod removed", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("STOP: " + (str(error) if type(error) is RuntimeError else "Backup/recovery incomplete (" + type(error).__name__ + ")") + "; values/raw errors withheld")
        raise SystemExit(1) from None
