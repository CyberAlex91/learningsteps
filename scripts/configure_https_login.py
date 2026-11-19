"""Preview/add only the public HTTPS Swagger SPA callback; preserve local URLs."""

import argparse
import json
import sys
from uuid import UUID
from check_private_db_login import capture

CLIENT = "7f3bbd70-2330-4f0c-8ecd-1e66936aaa15"
OBJECT = "c394f27a-0b77-425f-89f7-411619799cc7"
TENANT = "c0531484-50fa-4ff2-97df-b1f2d4810603"
CALLBACK = "https://learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com/docs/oauth2-redirect"


def read_app():
    return json.loads(capture([
        "az", "ad", "app", "show", "--id", CLIENT,
        "--query", "{id:id,appId:appId,redirectUris:spa.redirectUris}", "-o", "json",
    ]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Add HTTPS callback and verify")
    args = parser.parse_args()
    tenant = capture(["az", "account", "show", "--query", "tenantId", "-o", "tsv"])
    if tenant != TENANT:
        raise RuntimeError("Expected LearningSteps Entra tenant")
    app = read_app()
    if app["appId"] != CLIENT or str(UUID(app["id"])) != OBJECT:
        raise RuntimeError("Unexpected Swagger application identity")
    existing = app.get("redirectUris") or []
    if not isinstance(existing, list) or not all(isinstance(url, str) for url in existing):
        raise RuntimeError("Unexpected redirect configuration")
    desired = list(existing)
    if CALLBACK not in desired:
        desired.append(CALLBACK)
    print("Application: LearningSteps-Alex-Swagger")
    print("Existing SPA callbacks: " + json.dumps(existing))
    print("HTTPS callback: " + CALLBACK)
    if not args.apply:
        print("Preview only; run with --apply to add the callback. No new permissions or secrets.")
        return
    if desired != existing:
        capture([
            "az", "rest", "--method", "PATCH",
            "--url", "https://graph.microsoft.com/v1.0/applications/" + OBJECT,
            "--headers", "Content-Type=application/json",
            "--body", json.dumps({"spa": {"redirectUris": desired}}), "--output", "none",
        ])
    actual = read_app().get("redirectUris") or []
    if CALLBACK not in actual or not set(existing).issubset(actual):
        raise RuntimeError("Callback update not confirmed")
    print("PASS: HTTPS callback registered; existing callbacks retained")
    print("No client secret or new API permissions created.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error) if type(error) is RuntimeError else type(error).__name__
        print("STOP: " + message, file=sys.stderr)
        sys.exit(1)
