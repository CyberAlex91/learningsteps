#!/usr/bin/env bash
# Zweck: Prüft das festgelegte Gateway-Image auf HIGH-/CRITICAL-Schwachstellen ohne Bereitstellung.
# Local-only candidate assessment. Never uploads or deploys an image.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$project_dir"
docker_desktop="/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
gateway_image="traefik:v2.11.61"
scanner="ghcr.io/aquasecurity/trivy@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb"

"$docker_desktop" pull --platform linux/amd64 "$gateway_image"
"$docker_desktop" image inspect "$gateway_image" --format '{{index .RepoDigests 0}}'
"$docker_desktop" run --rm --network none "$gateway_image" version
mkdir -p artifacts/security
archive_path=$(wslpath -w "$PWD/artifacts/security/traefik-gateway.tar")
scan_path=$(wslpath -w "$PWD/artifacts/security")
"$docker_desktop" image save --output "$archive_path" "$gateway_image"
"$docker_desktop" run --rm \
  --mount "type=bind,source=$scan_path,target=/scan,readonly" \
  --mount "type=volume,source=learningsteps-trivy-cache,target=/root/.cache/trivy" \
  "$scanner" image --input /scan/traefik-gateway.tar \
  --scanners vuln --severity HIGH,CRITICAL --exit-code 1 --timeout 10m --format table \
  | tee artifacts/security/traefik-gateway-trivy.txt
echo "PASS: gateway candidate vulnerability gate passed; nothing uploaded or deployed."
