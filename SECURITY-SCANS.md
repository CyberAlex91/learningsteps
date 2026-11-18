# LearningSteps Evolution – image security checks

## Current acceptance: Alpine application image passed (2026-11-18)

The user's completed Trivy report at 12:35 UTC reports zero HIGH/CRITICAL
findings for Alpine 3.24.4 and all listed Python packages, exit code 0.
This is a vulnerability scan at the selected severity and database snapshot,
not a guarantee of absence of vulnerabilities of every severity or secrets.
No ignore rules or --ignore-unfixed were used. Dependency check and isolated
non-root, read-only startup/anonymous-route rejection smoke test also passed.

- Accepted local image tag: learningsteps-api:evolution-alpine.
- Image config digest from build output:
  sha256:d094dbc847894a0e0c9dbab87963fd6a04a4a4237605dc544a98bfcb2c448294.
- Build manifest list from output:
  sha256:de2ed68b2b5d9b6a253d08155d8ccd307d532fa489b0bab7a755b186476de2df.
- Base: python:3.12-alpine at
  sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89.
- apk upgrade --no-cache applied; Python dependency lock unchanged, binary wheels only.
- Dockerfile now uses these accepted build steps; temporary Dockerfile.alpine removed.
- The separate apk info attempt made without networking did not confirm an exact
  installed krb5 version. The completed full-image scan is the acceptance evidence.
- No actual PostgreSQL transaction or Foundry inference in this Alpine image has
  been verified yet; later integration tests remain necessary.
- Upload completed according to user Docker push output on 2026-11-18:
  `acrlearningstepsalex0ad5f630.azurecr.io/learningsteps-api:evolution-cc8174d`.
  ACR reported digest
  `sha256:de2ed68b2b5d9b6a253d08155d8ccd307d532fa489b0bab7a755b186476de2df`,
  matching the scanned build's manifest list. Docker image inspect `.Id` on
  this installation also returned this manifest digest, not the separate config
  digest shown in the build output. The upload reused this image without rebuilding.
  A new build must be scanned again because apk repositories and vulnerability
  data can change. No AKS deployment has been performed yet.

Earlier failed attempts below remain documented as evidence of enforcement.

## 2026-11-18: first scan blocks upload

User supplied a completed Trivy scan with exit code 1. The report lists
101 HIGH/CRITICAL findings in Debian 12.15 packages (99 HIGH, 2 CRITICAL).
The Python package targets shown in the report have no HIGH/CRITICAL findings.
These are package/advisory findings, not 101 independently verified exploit paths.
Several OS findings have no fixed version listed; do not bypass the gate using
`--ignore-unfixed` or a blanket ignore file.

- Application image: learningsteps-api:evolution, Linux AMD64.
- Base: python:3.12-slim-bookworm at
  sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df.
- Scanner: Trivy 0.76.2 at
  ghcr.io/aquasecurity/trivy@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb.
- Scan: image archive, scanners vuln, severity HIGH,CRITICAL, exit-code 1;
  database downloaded on 2026-11-18. Archive mounted read-only, no Docker socket
  or Azure credentials exposed to the scanner.
- Non-root startup and anonymous-route rejection smoke test passed beforehand.
- No application image upload to ACR has been confirmed.

Next remediation candidate: official python:3.12-slim-trixie, keeping the Python
minor version and application dependency lock unchanged. Pull, record digest,
build separately, rerun dependency/startup tests and vulnerability scan before
changing the approved Dockerfile default. Improvement is not yet confirmed.
Any remaining advisory needs individual review; no scan exclusions approved.

## 2026-11-18: Trixie candidate still blocked

Official python:3.12-slim-trixie at
sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
was built separately as learningsteps-api:evolution-trixie. Package consistency
and the isolated hardened startup/authentication smoke test passed.
The subsequent user-supplied Trivy output reports 48 HIGH, 0 CRITICAL,
exit code 1. The image is not approved for upload. The zlib1g finding lists
a fixed Debian package version; many other remaining findings have no fixed
version shown. A blanket apt upgrade cannot be assumed to clear this gate.

Next: evaluate the official Python 3.12 Alpine base with the same scan before
adapting the application build. Alpine uses musl rather than glibc; wheel
availability and runtime compatibility must be tested if this candidate passes.
No Alpine application build or scan success is confirmed yet.

## 2026-11-18: Alpine base has a fixable package finding

User's base-image scan detected Alpine 3.24.4, 16 HIGH and 0 CRITICAL,
exit code 1. All listed findings refer to krb5-libs 1.22.2-r1, with fixed
version 1.22.3-r0. No image digest was included in this pasted output.
`Dockerfile.alpine` is an evaluation candidate: apk upgrade --no-cache,
unchanged Python dependency lock, binary wheels only, UID/GID 10001.
The actual installed patch version, wheel compatibility and final vulnerability
scan remain unconfirmed. Main Dockerfile still uses the prior Bookworm base.
