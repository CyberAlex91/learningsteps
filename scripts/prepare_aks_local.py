"""Save local AKS user/IP inputs, without passwords or tokens; no Azure writes."""

import ipaddress
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen
from uuid import UUID


def main():
    target = Path(__file__).resolve().parents[1] / "infra-terraform" / "aks.local.auto.tfvars.json"
    if target.exists():
        raise SystemExit("Local AKS inputs already exist; not overwriting. Review before refreshing.")
    user_id = subprocess.check_output(
        ["az", "ad", "signed-in-user", "show", "--query", "id", "--output", "tsv"],
        text=True,
    ).strip()
    user_id = str(UUID(user_id))
    # The external service sees the request's source IP, no Azure credential.
    with urlopen("https://api.ipify.org", timeout=15) as response:
        address = ipaddress.IPv4Address(response.read(128).decode().strip())
    if not address.is_global:
        raise SystemExit("Expected a public IPv4 address")
    config = {"aks_admin_object_id": user_id, "aks_api_allowed_cidr": f"{address}/32"}
    with target.open("x", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
    print("Saved local administrator ID and public IPv4 /32; no tokens or passwords.")
    print("File: infra-terraform/aks.local.auto.tfvars.json (excluded from Git).")


if __name__ == "__main__":
    main()
