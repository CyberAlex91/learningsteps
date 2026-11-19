#!/usr/bin/env bash
# Zweck: Prüft den Gateway-Image-Digest und liefert das HTTPS-Manifest nach AKS aus.
# Deploy only the already scanned gateway digest and its explicit manifests.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$project_dir"
docker_desktop="/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
subscription="0ad5f630-c506-401a-93fa-36b0fe313829"
digest="sha256:262ccbae7ee89fbc17b2ec1c2c4718b48d4b4a7a38c8c26a8593b074fdbc7844"
platform_digest="sha256:665efb2d37f2458cc2e0bdde996df05387ab4046bde946dff3654c1077d7efe1"
registry="acrlearningstepsalex0ad5f630"
image="$registry.azurecr.io/learningsteps-gateway:traefik-2.11.61"

if [ "$(kubectl config current-context)" != "aks-learningsteps-evolution" ]; then
  echo "STOP: unexpected Kubernetes context."; exit 1
fi
if [ "$(az account show --query id -o tsv)" != "$subscription" ]; then
  echo "STOP: select the LearningSteps subscription first."; exit 1
fi
local_platform=$("$docker_desktop" image inspect "traefik@$digest" --format '{{.Os}}/{{.Architecture}}')
if [ "$local_platform" != "linux/amd64" ]; then
  echo "STOP: expected the scanned Linux/AMD64 image."; exit 1
fi

# A multi-platform index and its AMD64 manifest have different digests.
# Verify membership against the pinned publisher index, never a mutable tag.
mkdir -p artifacts/security
"$docker_desktop" buildx imagetools inspect "docker.io/library/traefik@$digest" \
  --raw > artifacts/security/traefik-source-index.json
python3 - "$platform_digest" <<'PY'
import json
from pathlib import Path
import sys
index = json.loads(Path("artifacts/security/traefik-source-index.json").read_text())
matches = [m["digest"] for m in index.get("manifests", [])
           if m.get("platform", {}).get("os") == "linux"
           and m.get("platform", {}).get("architecture") == "amd64"]
if matches != [sys.argv[1]]:
    raise SystemExit("STOP: published Linux/AMD64 manifest does not match expected digest.")
print("PASS: AMD64 digest verified in the pinned original multi-platform index.")
PY

az acr login --name "$registry" --subscription "$subscription" \
  --expose-token --query accessToken -o tsv |
  "$docker_desktop" login "$registry.azurecr.io" \
    --username 00000000-0000-0000-0000-000000000000 --password-stdin
"$docker_desktop" tag "traefik@$digest" "$image"
"$docker_desktop" push "$image"
remote_digest=$(az acr repository show --name "$registry" \
  --image learningsteps-gateway:traefik-2.11.61 --subscription "$subscription" \
  --query digest -o tsv)
if [ "$remote_digest" != "$platform_digest" ]; then
  echo "STOP: registry digest mismatch."; exit 1
fi
echo "PASS: ACR contains the verified Linux/AMD64 manifest."

kubectl apply --dry-run=server -f app/k8s-manifests/gateway/traefik.yaml
kubectl apply -f app/k8s-manifests/gateway/traefik.yaml
kubectl rollout status deployment/learningsteps-https -n learningsteps --timeout=600s
kubectl get pods,pvc,service -n learningsteps
echo "Gateway rollout complete. Public IP/DNS and certificate issuance may still be converging."
echo "Next: python3 app/scripts/check_https_access.py"
