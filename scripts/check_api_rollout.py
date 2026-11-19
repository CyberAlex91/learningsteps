"""Read-only checks of each API replica and its internal Kubernetes service."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from check_private_db_login import capture

REMOTE = r'''
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

checks = []
try:
    cases = [("http://127.0.0.1:8000", "/health/live", "GET", 200),
             ("http://127.0.0.1:8000", "/health/ready", "GET", 200),
             ("http://127.0.0.1:8000", "/entries", "GET", 401),
             ("http://127.0.0.1:8000", "/me/notes/summary", "POST", 401)]
    if sys.argv[1] == "service":
        cases.append(("http://learningsteps-api", "/health/ready", "GET", 200))
    for base, path, method, expected in cases:
        request = Request(base + path, method=method,
                          data=b"{}" if method == "POST" else None,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=8) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
        if status != expected:
            raise RuntimeError()
        checks.append({"path": path, "method": method, "status": status,
                       "target": "service" if "learningsteps-api" in base else "pod"})
    print(json.dumps(checks))
except Exception as error:
    print("API acceptance failed: " + type(error).__name__, file=sys.stderr)
    raise SystemExit(1)
'''


def main():
    if capture(["kubectl", "config", "current-context"]) != "aks-learningsteps-evolution":
        raise RuntimeError("Expected LearningSteps AKS context")
    pods = json.loads(capture(["kubectl", "get", "pods", "-n", "learningsteps",
                               "-l", "app=learningsteps-api", "-o", "json"]))["items"]
    active = [p for p in pods if not p["metadata"].get("deletionTimestamp")]
    if len(active) < 2 or any(not any(c["type"] == "Ready" and c["status"] == "True"
                                     for c in p.get("status", {}).get("conditions", []))
                              for p in active):
        raise RuntimeError("Expected at least two Ready API pods")
    evidence = {"checked_at": datetime.now(timezone.utc).isoformat(), "pods": []}
    for index, pod in enumerate(active):
        name = pod["metadata"]["name"]
        checks = json.loads(capture(["kubectl", "exec", name, "-n", "learningsteps",
                                     "-c", "api", "--", "python", "-c", REMOTE,
                                     "service" if index == 0 else "pod"]))
        evidence["pods"].append({"name": name, "checks": checks})
        print(f"PASS: {name}: live/ready 200, anonymous notes/summary 401")
    print("PASS: internal Service DNS and routing to a ready API backend")
    hpa = json.loads(capture(["kubectl", "get", "hpa", "learningsteps-api", "-n",
                              "learningsteps", "-o", "json"]))
    measured = any(m.get("resource", {}).get("name") == "cpu"
                   and m["resource"].get("current", {}).get("averageUtilization") is not None
                   for m in hpa.get("status", {}).get("currentMetrics", []))
    evidence["hpa_cpu_metrics_present"] = measured
    evidence["autoscaling_load_test_performed"] = False
    print("HPA CPU measurements: " + ("available" if measured else "not available yet"))
    target = Path(__file__).resolve().parents[2] / "artifacts/azure/api-rollout-check.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("Evidence: artifacts/azure/api-rollout-check.json; no note changes")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error) if type(error) is RuntimeError else type(error).__name__
        print("STOP: " + message, file=sys.stderr)
        sys.exit(1)
