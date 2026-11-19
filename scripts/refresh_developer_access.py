# Zweck: Prüft die aktuelle Entwickler-IP und bereitet optional einen eng begrenzten Terraform-Zugangsplan vor.
"""Detect the developer IPv4; optionally prepare a reviewed Terraform IP plan.

Run in WSL. Default is read-only. --prepare adds the exact current /32 to
Key Vault so Terraform can refresh secrets, updates local inputs and plans.
Never applies a plan, starts services, reads secrets or broadens access to /0.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen

SUBSCRIPTION = "0ad5f630-c506-401a-93fa-36b0fe313829"
TENANT = "c0531484-50fa-4ff2-97df-b1f2d4810603"
APP = Path(__file__).resolve().parents[1]
INFRA = APP / "infra-terraform"
LOCAL = INFRA / "aks.local.auto.tfvars.json"


def azure_json(*args):
    result = subprocess.run(
        ["az", *args, "--output", "json", "--only-show-errors"],
        check=True, capture_output=True, text=True, timeout=90,
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true",
                        help="Update local IP, allow it in Key Vault, save Terraform plan")
    options = parser.parse_args()
    account = azure_json("account", "show")
    if account["id"] != SUBSCRIPTION or account["tenantId"] != TENANT:
        raise SystemExit("Select Alexander Plank - Sub in the correct tenant first.")

    config = json.loads(LOCAL.read_text(encoding="utf-8-sig"))
    # Public IP service receives no Azure credentials. Reject IPv6/private data.
    with urlopen("https://api.ipify.org", timeout=15) as response:
        address = ipaddress.IPv4Address(response.read(128).decode().strip())
    if not address.is_global:
        raise SystemExit("Expected a global public IPv4; no changes made.")
    cidr = f"{address}/32"
    cluster = azure_json(
        "aks", "show", "--subscription", SUBSCRIPTION,
        "--resource-group", "rg-learningsteps-evolution",
        "--name", "aks-learningsteps-evolution",
        "--query", "apiServerAccessProfile.authorizedIpRanges",
    )
    print(f"Current public IPv4: {cidr}")
    print(f"Local Terraform IPv4: {config.get('aks_api_allowed_cidr')}")
    print(f"AKS allowed IPv4 ranges: {cluster}")
    if not options.prepare:
        print("Read-only check. Use --prepare to prepare an IP update plan.")
        return

    # Bootstrap only the new /32: without this, a changed IP prevents Terraform
    # refreshing existing vault secrets. Terraform removes obsolete rules on apply.
    subprocess.run([
        "az", "keyvault", "network-rule", "add", "--subscription", SUBSCRIPTION,
        "--resource-group", "rg-learningsteps-evolution",
        "--name", "kv-lsteps-0ad5f630", "--ip-address", cidr,
        "--output", "none", "--only-show-errors",
    ], check=True, timeout=90)
    config["aks_api_allowed_cidr"] = cidr
    temporary = LOCAL.with_suffix(".json.tmp")
    try:
        temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, LOCAL)
    finally:
        temporary.unlink(missing_ok=True)
    print("Local inputs updated; other settings preserved. Current /32 allowed in vault.")
    print("Preparing plan only. Review ALL changes before applying.", flush=True)
    subprocess.run([
        "terraform", f"-chdir={INFRA}", "plan", "-out=developer-ip.tfplan",
    ], check=True)
    print("No apply performed. After review, run:")
    print("terraform -chdir=app/infra-terraform apply developer-ip.tfplan")
    print("Then verify No changes and kubectl get nodes --request-timeout=10s.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        # Do not expose captured Azure output (account metadata/errors).
        raise SystemExit(f"Command failed (exit {error.returncode}); stopped without apply.")
