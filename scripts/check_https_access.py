# Zweck: Prüft öffentliches HTTPS mit gültigem Zertifikat und geschützten Notizendpunkten.
"""Verify public HTTPS, redirect and anonymous rejection; no credentials used."""

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import ssl

HOST = "learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check():
    results = []
    for path, expected in (("/health/ready", 200), ("/docs", 200), ("/entries", 401)):
        try:
            # Default TLS context checks public CA trust and hostname. Never -k.
            with urlopen("https://" + HOST + path, timeout=8) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
        if status != expected:
            raise RuntimeError("HTTPS response not ready")
        results.append({"path": path, "status": status})
    opener = build_opener(NoRedirect())
    try:
        with opener.open(Request("http://" + HOST + "/docs"), timeout=8):
            raise RuntimeError("HTTP did not redirect")
    except HTTPError as error:
        location = error.headers.get("Location", "")
        if error.code not in (301, 302, 307, 308) or location not in (
                "https://" + HOST + "/docs", "https://" + HOST + ":443/docs"):
            raise RuntimeError("Unexpected redirect")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=60,
                        help="Overall retry window in seconds (default 60)")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 300:
        parser.error("timeout must be between 1 and 300 seconds")
    print(f"Checking DNS, trusted HTTPS and redirect (retry window {args.timeout}s)...", flush=True)
    deadline = time.monotonic() + args.timeout
    last_reason = None
    while True:
        try:
            results = check()
            break
        except (URLError, OSError, ssl.SSLError, RuntimeError) as error:
            # Safe diagnostics only: exception class or HTTP status, never body.
            if isinstance(error, HTTPError):
                reason = "HTTP " + str(error.code)
            elif isinstance(error, URLError):
                reason = type(error.reason).__name__
            else:
                reason = type(error).__name__
            if reason != last_reason:
                print("Waiting: " + reason, flush=True)
                last_reason = reason
            if time.monotonic() >= deadline:
                raise SystemExit("STOP: public HTTPS not ready (" + reason + "). Inspect gateway logs; TLS verification remains enabled.")
            time.sleep(5)
    evidence = {"checked_at": datetime.now(timezone.utc).isoformat(),
                "hostname": HOST, "certificate_chain_and_hostname_verified": True,
                "http_redirect_to_https": True, "responses": results,
                "authenticated_user_flow_tested": False}
    target = Path(__file__).resolve().parents[2] / "artifacts/azure/https-access-check.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("PASS: trusted certificate and hostname; HTTPS docs/readiness 200; anonymous entries 401")
    print("PASS: HTTP redirects to public HTTPS port 443")
    print("Evidence: artifacts/azure/https-access-check.json")
    print("Next: register the exact HTTPS Swagger callback in Entra, then test login.")


if __name__ == "__main__":
    main()
