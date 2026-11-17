#!/usr/bin/env bash
# Development container only. Do not install the CLI in the API virtualenv.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' 'Run with docker exec --user root.' >&2
    exit 1
fi

cli_dir=/opt/learningsteps-azure-cli
if [ ! -x "$cli_dir/bin/az" ]; then
    python3 -m venv "$cli_dir"
    "$cli_dir/bin/python" -m pip install --disable-pip-version-check \
        --index-url https://pypi.org/simple 'azure-cli==2.93.0'
fi

if [ -e /usr/local/bin/az ] || [ -L /usr/local/bin/az ]; then
    if [ "$(readlink -f /usr/local/bin/az)" != "$cli_dir/bin/az" ]; then
        printf '%s\n' 'Existing az launcher was not replaced; inspect it first.' >&2
        exit 1
    fi
else
    ln -s "$cli_dir/bin/az" /usr/local/bin/az
fi

# Metadata only. This does not sign in or print credentials.
AZURE_CORE_COLLECT_TELEMETRY=false "$cli_dir/bin/az" version
