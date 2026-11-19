# Zweck: Prüft alle lokal verfügbaren Git-Verweise auf Geheimnisse, ohne lokale Arbeitsgeheimnisse einzubinden.
"""Scan all locally available Git refs without mounting working-tree secrets."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

APP = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
DOCKER = "/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError("Preparation command failed; raw output withheld")
    return result.stdout.strip()


def main():
    if os.name != "posix" or not Path(DOCKER).exists():
        raise RuntimeError("Run in WSL with Docker Desktop available")
    if run(["git", "-C", str(APP), "rev-parse", "--is-shallow-repository"]) != "false":
        raise RuntimeError("Shallow repository: obtain full history before scanning")
    out = APP.parent / "artifacts/security"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report = out / ("git-history-" + stamp + ".json")
    # Mirror copies only Git objects/refs, never untracked .env or local secrets.
    with tempfile.TemporaryDirectory(prefix="history-mirror-", dir=out) as directory:
        mirror = Path(directory) / "repo.git"
        run(["git", "clone", "--mirror", "--no-hardlinks", "--quiet", str(APP), str(mirror)])
        commits = int(run(["git", "--git-dir", str(mirror), "rev-list", "--all", "--count"]))
        source_windows = run(["wslpath", "-w", str(mirror)])
        output_windows = run(["wslpath", "-w", str(out)])
        reviewed_windows = run(["wslpath", "-w", str(APP / "security/gitleaks-reviewed-fingerprints.txt")])
        print(f"Scanning {commits} commits across all locally available refs...", flush=True)
        result = subprocess.run([
            DOCKER, "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges=true",
            "--env", "GIT_CONFIG_COUNT=1", "--env", "GIT_CONFIG_KEY_0=safe.directory",
            "--env", "GIT_CONFIG_VALUE_0=/repo",
            "--mount", f"type=bind,source={source_windows},target=/repo,readonly",
            "--mount", f"type=bind,source={output_windows},target=/out",
            "--mount", f"type=bind,source={reviewed_windows},target=/reviewed-fingerprints,readonly",
            IMAGE, "git", "/repo", "--log-opts=--all", "--redact=100", "--no-banner",
            "--log-level", "error", "--ignore-gitleaks-allow",
            "--gitleaks-ignore-path", "/reviewed-fingerprints",
            "--report-format", "json", "--report-path", "/out/" + report.name,
            "--timeout", "300", "--exit-code", "1",
        ], capture_output=True, text=True, timeout=360)
    if result.returncode not in (0, 1) or not report.exists():
        raise RuntimeError("Scanner failed; no clean result established; raw output withheld")
    findings = json.loads(report.read_text(encoding="utf-8")) or []
    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "image": IMAGE,
        "commits_available": commits, "scope": "all local refs; no remote fetch performed",
        "scanner_exit_code": result.returncode, "finding_count": len(findings),
        "reviewed_false_positive_fingerprints": sum(
            bool(line.strip()) and not line.lstrip().startswith("#")
            for line in (APP / "security/gitleaks-reviewed-fingerprints.txt").read_text().splitlines()
        ),
        "redacted_report": report.name,
        "findings": [{"rule": f.get("RuleID"), "file": f.get("File"),
                      "commit": f.get("Commit"), "line": f.get("StartLine")}
                     for f in findings],
    }
    (out / "git-history-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Evidence: artifacts/security/git-history-summary.json")
    if result.returncode or findings:
        raise RuntimeError(f"{len(findings)} potential secret findings require review; values withheld")
    print("PASS: no secrets detected in available Git history; no Azure changes")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit("STOP: " + (str(error) if isinstance(error, RuntimeError)
                                     else "Scanner/preparation timed out")) from None
