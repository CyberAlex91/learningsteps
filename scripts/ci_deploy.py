# Zweck: Liefert in vertrauenswürdigen GitHub-Läufen einen geprüften Image-Digest über AKS Run Command aus.
"""Trusted-push-only API image rollout via ARM; never print app config/secrets."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

PREFIX = "acrlearningstepsalex0ad5f630.azurecr.io/learningsteps-api@sha256:"
SUBSCRIPTION = "0ad5f630-c506-401a-93fa-36b0fe313829"


def main():
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REPOSITORY") != "CyberAlex91/learningsteps"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"):
        raise SystemExit("STOP: delivery requires the trusted GitHub push context")
    image = os.environ.get("IMAGE_REF", "")
    revision = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(re.escape(PREFIX) + "[0-9a-f]{64}", image):
        raise SystemExit("STOP: expected a verified project ACR digest")
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise SystemExit("STOP: invalid Git revision")
    # Only this fixed command set runs in the cluster. No logs, secrets or SQL.
    command = "\n".join([
        "set -eu",
        "kubectl -n learningsteps set image deployment/learningsteps-api api=" + shlex.quote(image),
        "kubectl -n learningsteps rollout status deployment/learningsteps-api --timeout=180s",
        "kubectl -n learningsteps get deployment learningsteps-api "
        "-o jsonpath='{.spec.template.spec.containers[?(@.name==\"api\")].image}'",
    ])
    result = subprocess.run([
        "az", "aks", "command", "invoke", "--subscription", SUBSCRIPTION,
        "--resource-group", "rg-learningsteps-evolution", "--name", "aks-learningsteps-evolution",
        "--command", command, "--output", "json", "--only-show-errors",
    ], capture_output=True, text=True, timeout=600)
    if result.returncode:
        # A fixed Azure error code is useful without dumping raw credential logs.
        match = re.search(r"\(([A-Za-z][A-Za-z0-9_]{0,79})\)", result.stderr)
        code = match.group(1) if match else "AzureCommandError"
        raise SystemExit("STOP: AKS Run Command request failed (" + code + ")")
    try:
        execution = json.loads(result.stdout)
    except ValueError:
        raise SystemExit("STOP: Azure returned no structured command result") from None
    if execution.get("exitCode") != 0:
        raise SystemExit("STOP: cluster image update/rollout command failed; inspect deployment status")
    if image not in execution.get("logs", ""):
        raise SystemExit("STOP: deployed image digest not confirmed")
    evidence = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "revision": revision, "image": image,
        "cluster": "aks-learningsteps-evolution", "namespace": "learningsteps",
        "deployment": "learningsteps-api", "rollout_succeeded": True,
        "database_notes_modified": False,
    }
    target = Path(os.environ["RUNNER_TEMP"]) / "deployment-evidence.json"
    target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("PASS: AKS rollout completed with verified image " + image)
    print("Revision: " + revision)


if __name__ == "__main__":
    main()
