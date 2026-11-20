# Zweck: Packt ausschließlich versionierte Quellen, finale Dokumente und freigegebene Nachweise in eine geprüfte geheimnisfreie Abgabe-ZIP.
"""Run only after final recovery acceptance and committing the documentation."""

import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
EVIDENCE = [
    "azure/private-db-network-check.txt", "azure/private-db-login-check.json",
    "azure/cloud-database-schema-check.json", "azure/workload-access-check.json",
    "azure/https-access-check.json", "azure/api-rollout-check.json",
    "azure/pod-recovery-check.json", "azure/hpa-scaling-check.json",
    "azure/foundry-runtime-deployment.json", "azure/foundry-runtime-apply-check.json",
    "azure/foundry-workload-inference-check.json", "azure/cloud-stored-note-summary-check.json",
    "azure/data-check-check.json", "azure/data-current-check.json",
    "azure/restore-empty-rejection-check.json", "azure/data-restore-empty-check.json",
    "azure/terraform-destroy-check.json", "azure/evolution-recovery-final.json",
    "azure/foundry-after-recovery-check.json", "github/main-delivery-final.json",
    "github/security-gate-negative-log.txt", "github/security-gate-proof-request.json",
    "github/history-scan-and-delivery-44534120752.json", "github/foundry-delivery-44536752654.json",
    "security/terraform-trivy.txt", "security/traefik-gateway-trivy.txt",
    "security/git-history-summary.json",
    "azure/lifecycle-down-check.json", "azure/backend-recreation-check.json",
    "github/offline-lifecycle-ci-final.json",
    "history/20261119/terraform-destroy-check.json", "history/20261119/evolution-recovery-final.json",
]


def git(*args):
    return subprocess.check_output(["git", "-C", str(APP), "-c", "core.autocrlf=input", *args])


def main():
    final = json.loads((ROOT / "artifacts/azure/evolution-recovery-final.json").read_text(encoding="utf-8"))
    if final.get("passed") is not True:
        raise SystemExit("Actual recovery acceptance is required")
    off = json.loads((ROOT / "artifacts/azure/lifecycle-down-check.json").read_text(encoding="utf-8"))
    if not off.get("passed") or off.get("active_project_resource_count") != 0:
        raise SystemExit("Verified complete cloud shutdown is required for the final offline package")
    if git("status", "--porcelain").strip():
        raise SystemExit("Commit reviewed source/documentation changes before packaging")
    revision = git("rev-parse", "HEAD").decode().strip()
    data = {}
    with zipfile.ZipFile(io.BytesIO(git("archive", "--format=zip", "HEAD"))) as source:
        for info in source.infolist():
            if not info.is_dir():data["app/" + info.filename] = source.read(info)
    for filename, category in [("LearningSteps-Evolution-Projektbericht.pdf", "Bericht"),
                               ("LearningSteps-Evolution-Ablauf.pdf", "Anleitung")]:
        data[category + "/" + filename] = (ROOT / "output/pdf" / filename).read_bytes()
    for relative in EVIDENCE:
        path = ROOT / "artifacts" / relative
        if not path.is_file():raise SystemExit("Required evidence missing: " + relative)
        data["artifacts/" + relative] = path.read_bytes()
    for filename in ("Start-Lokal.ps1", "Stop-Lokal.ps1"):
        data[filename] = (ROOT / filename).read_bytes()
    introduction = '''<!-- Zweck: Leitet durch die abschließende LearningSteps-Evolution-Abgabe. -->
# LearningSteps Evolution Abgabe

Alexander Plank | 20.11.2026

- Bericht/LearningSteps-Evolution-Projektbericht.pdf: technischer Bericht mit Ergebnis und Grenzen.
- Anleitung/LearningSteps-Evolution-Ablauf.pdf: separate Erklärung zum Verstehen und Nachmachen.
- app/: versionierte Quellen, Terraform, Kubernetes, Tests und Anleitungen.
- artifacts/: ausgewählte tokenfreie Nachweise; keine privaten Sicherungen.
- FILE-MANIFEST.sha256: Prüfsummen aller übrigen Paketdateien.

Für den tatsächlichen Betrieb werden eigene lokale Anmeldung und private Konfiguration
benötigt. Die Wiederherstellung vorhandener Daten benötigt die separat aufbewahrten
verschlüsselten Backups und ihre Schlüssel. Beides ist absichtlich nicht in dieser
Abgabe enthalten. Der Remote-State-Speicher wird bei Bedarf ebenfalls neu erstellt.
Die Cloud ist vollständig abgebaut, einschließlich Remote-State-Speicher.
Wiederherstellung: python3 app/scripts/lifecycle.py up (WSL, ursprünglicher
Projektordner mit privaten Sicherungen). Einzelheiten in app/RECOVERY.md.
Prometheus/Grafana ist ausdrücklich optional und wurde nicht implementiert.
'''
    data["START-HIER.md"] = introduction.encode()
    data["VERSION.json"] = json.dumps({"git_commit": revision, "repository": "https://github.com/CyberAlex91/learningsteps",
                                        "recovery_passed": True, "cloud_state": "fully_removed_including_backend",
                                        "private_material_included": False}, indent=2).encode()
    patterns = [re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
                re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")]
    for name, blob in data.items():
        parts = Path(name).parts
        if any(part in {".git", ".secrets", ".state", ".terraform", "venv", "__pycache__"} for part in parts):
            raise SystemExit("Private/generated path in package")
        if Path(name).name == ".env" or name.endswith((".key", ".pem", ".enc", ".tar", ".tfplan")):
            raise SystemExit("Private/runtime artifact in package")
        if not name.endswith(".pdf"):
            text = blob.decode("utf-8-sig", errors="replace")
            if any(pattern.search(text) for pattern in patterns):
                raise SystemExit("Potential credential pattern in " + name + "; values withheld")
    hashes = {name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(data.items())}
    data["FILE-MANIFEST.sha256"] = "\n".join(h + "  " + name for name, h in hashes.items()).encode() + b"\n"
    out = ROOT / "Abgabe"; out.mkdir(exist_ok=True)
    target = out / "LearningSteps-Evolution-Abgabe-Final.zip"
    temporary = target.with_suffix(".tmp.zip")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, blob in sorted(data.items()):package.writestr(name, blob)
    with zipfile.ZipFile(temporary) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == set(data)
        for name, expected in hashes.items():assert hashlib.sha256(package.read(name)).hexdigest() == expected
    temporary.replace(target)
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(checksum + "  " + target.name + "\n")
    (ROOT / "artifacts/azure/submission-package-check.json").write_text(json.dumps({
        "passed": True, "files": len(data), "git_commit": revision, "zip_sha256": checksum,
        "private_paths_excluded": True, "zip_integrity_and_file_hashes_verified": True,
    }, indent=2) + "\n")
    print("PASS: " + str(len(data)) + " allowlisted files; ZIP and individual hashes verified")
    print(target)


if __name__ == "__main__":
    main()
