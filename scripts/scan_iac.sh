#!/usr/bin/env bash
# Zweck: Prüft eine temporäre Kopie der Terraform-Quellen auf HIGH-/CRITICAL-Fehlkonfigurationen.
# Assess tracked Terraform source locally; never mount state or local tfvars.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$project_dir"
docker_desktop="/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
mkdir -p artifacts/security
source_dir=$(mktemp -d "$PWD/artifacts/security/iac-source.XXXXXX")
cp app/infra-terraform/*.tf "$source_dir/"
# Synthetic static-analysis inputs only. Never pass these to terraform apply.
printf '%s\n' \
  'aks_admin_object_id = "00000000-0000-0000-0000-000000000001"' \
  'aks_api_allowed_cidr = "203.0.113.10/32"' \
  > "$source_dir/security-scan.tfvars"
source_windows=$(wslpath -w "$source_dir")
"$docker_desktop" run --rm \
  --mount "type=bind,source=$source_windows,target=/src,readonly" \
  ghcr.io/aquasecurity/trivy@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb \
  config --tf-vars /src/security-scan.tfvars \
  --severity HIGH,CRITICAL --exit-code 1 --timeout 10m --format table /src \
  | tee artifacts/security/terraform-trivy.txt
echo "PASS: Terraform HIGH/CRITICAL gate passed. No Azure changes."
