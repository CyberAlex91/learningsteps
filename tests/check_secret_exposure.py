"""Report patterns/counts only; never print matched secrets or log contents."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "jwt_value": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
}

paths = set()
for directory in (ROOT / "api", ROOT / "tests", ROOT / ".devcontainer", ROOT / "database"):
    for path in directory.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".json", ".sh", ".sql", ".yml", ".yaml", ".md"}:
            paths.add(path)
paths.update(ROOT.glob("*.md"))
paths.update((ROOT / "api").glob("requirements.*"))
paths.add(ROOT / "Dockerfile")

findings = []
for path in sorted(paths):
    content = path.read_text(encoding="utf-8-sig")
    for name, pattern in PATTERNS.items():
        if pattern.search(content):
            findings.append({"file": str(path.relative_to(ROOT)), "kind": name})

log_path = Path("/tmp/learningsteps-api.log")
log_available = log_path.is_file()
log = log_path.read_text(encoding="utf-8", errors="replace") if log_available else ""
log_matches = {name: len(pattern.findall(log)) for name, pattern in PATTERNS.items()}
note_markers = (
    "Ich habe mit Terraform ein virtuelles Netzwerk und getrennte Subnetze geplant.",
    "Ich musste verstehen, wie Terraform-State und State-Locking zusammenhängen.",
    "Als Nächstes möchte ich Remote State sicher einrichten.",
    "Ich habe bei Kubernetes den Unterschied zwischen Readiness- und Liveness-Probes gelernt.",
    "Mir war zunächst unklar, wann ein Pod keinen Traffic erhalten soll und wann er neu gestartet werden muss.",
    "Ich möchte eine Readiness-Probe für die LearningSteps-API konfigurieren.",
    "Ich habe LearningSteps mit Entra-Anmeldung und schlüssellosem Foundry-Zugriff verbunden.",
    "Die Nutzeranmeldung und die separate Anmeldung des Backends bei Foundry auseinanderzuhalten war schwierig.",
    "Ich möchte prüfen, ob die KI meine gespeicherten Lernnotizen korrekt zusammenfasst.",
)
note_matches = sum(marker in log for marker in note_markers)
report = {
    "success": not findings and log_available and not any(log_matches.values()) and note_matches == 0,
    "sourceFilesScanned": len(paths),
    "sourcePatternFindings": findings,
    "apiLogAvailable": log_available,
    "apiLogPatternCounts": log_matches,
    "knownSyntheticNoteFieldsInLog": note_matches,
    "rawMatchesPrinted": False,
    "privateConfigurationOrCredentialCacheRead": False,
    "scope": "Pattern scan and exact known test-note fields; not a guarantee of detecting every possible secret format",
}
print(json.dumps(report, indent=2))
sys.exit(0 if report["success"] else 1)
