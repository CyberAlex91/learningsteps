# Zweck: Erzeugt einen isolierten unsicheren Test-Commit zum Nachweis des CI-Sicherheitsabbruches.
"""Push an isolated negative IaC test without changing checkout/index/HEAD.

Creates a proof branch only. Never applies Terraform, merges, or deploys.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

APP = Path(__file__).resolve().parents[1]
FIXTURE = "infra-terraform/security-gate-negative.tf"
UNSAFE_TEST = '''# INTENTIONALLY INSECURE NEGATIVE CI TEST. Never merge or terraform apply.
resource "azurerm_network_security_group" "negative_ci_only" {
  name                = "DO-NOT-DEPLOY-negative-ci"
  location            = "germanywestcentral"
  resource_group_name = "DO-NOT-DEPLOY-NEGATIVE-CI"

  security_rule {
    name                       = "INTENTIONAL-OPEN-SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "0.0.0.0/0"
    destination_address_prefix = "*"
  }
}
'''


def git(*args, input=None, env=None):
    result = subprocess.run(["git", "-C", str(APP), *args], input=input,
                            env=env, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise SystemExit("STOP: Git operation failed (" + args[0] + "); no merge/apply performed")
    return result.stdout.strip()


def main():
    if os.name != "posix":
        raise SystemExit("Run this helper in WSL")
    branch = git("branch", "--show-current")
    if branch != "feature/user-notes-summary":
        raise SystemExit("STOP: expected the LearningSteps feature branch")
    if git("remote", "get-url", "origin") != "https://github.com/CyberAlex91/learningsteps.git":
        raise SystemExit("STOP: unexpected origin repository")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("STOP: commit/stash tracked working changes before creating proof")
    evidence = APP.parent / "artifacts/github/security-gate-proof-request.json"
    if evidence.exists():
        raise SystemExit("STOP: a proof request already exists; inspect it before another run")
    base = git("rev-parse", "HEAD")
    base_tree = git("rev-parse", "HEAD^{tree}")
    if git("ls-tree", "--name-only", base, "--", FIXTURE):
        raise SystemExit("STOP: negative fixture already exists in base")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    proof_branch = "proof/security-gate-" + stamp + "-" + uuid4().hex[:6]
    with tempfile.TemporaryDirectory(prefix="learningsteps-proof-index-") as directory:
        # Only this temporary index gets the fixture. Main checkout/index untouched.
        environment = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        git("read-tree", base_tree, env=environment)
        blob = git("hash-object", "-w", "--stdin", input=UNSAFE_TEST)
        git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + FIXTURE,
            env=environment)
        tree = git("write-tree", env=environment)
        commit = git("commit-tree", tree, "-p", base,
                     input="Prove security gate blocks intentionally open SSH rule\n")
    print("Pushing isolated proof branch: " + proof_branch, flush=True)
    git("push", "origin", commit + ":refs/heads/" + proof_branch)
    if git("rev-parse", "HEAD") != base or git("branch", "--show-current") != branch:
        raise SystemExit("STOP: unexpected checkout state; inspect Git before continuing")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": base, "proof_commit": commit, "proof_branch": proof_branch,
        "fixture": FIXTURE, "terraform_applied": False,
        "delivery_excluded_by_branch": True,
        "expected_result": "Terraform HIGH/CRITICAL gate fails; delivery skipped",
        "actual_pipeline_result": "not checked yet",
    }, indent=2) + "\n", encoding="utf-8")
    print("PASS: proof commit pushed; active branch, checkout and normal index unchanged")
    print("No Azure command or deployment was executed by this helper.")
    print("Evidence request: artifacts/github/security-gate-proof-request.json")
    print("Next: inspect the proof branch's GitHub Actions result; do not merge it.")


if __name__ == "__main__":
    main()
