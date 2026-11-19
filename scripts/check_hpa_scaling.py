# Zweck: Erzeugt begrenzte HTTP-Last und prüft Hochskalierung sowie Rückkehr zu zwei API-Pods.
"""Bounded internal HTTP load: verify HPA expansion and return to two replicas."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4

from check_pod_recovery import ready

NS = "learningsteps"
LOAD = r'''
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import threading
import time

deadline = time.monotonic() + 300
counts = {"http_200": 0, "errors": 0}
lock = threading.Lock()

def worker():
    connection = http.client.HTTPConnection("learningsteps-api", 80, timeout=3)
    while time.monotonic() < deadline:
        ok = False
        try:
            connection.request("GET", "/health/live")
            response = connection.getresponse()
            response.read()
            ok = response.status == 200
        except Exception:
            connection.close()
        with lock:
            counts["http_200" if ok else "errors"] += 1
    connection.close()

with ThreadPoolExecutor(max_workers=24) as pool:
    futures = [pool.submit(worker) for _ in range(24)]
    while time.monotonic() < deadline:
        time.sleep(10)
        with lock:
            print(json.dumps(counts), flush=True)
    for future in futures:
        future.result()
'''


def k(*args, body=None):
    result = subprocess.run(["kubectl", *args, "--request-timeout=20s"],
                            input=body, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Kubernetes request failed; inspect cluster access and test Job")
    return result.stdout.strip()


def sample():
    deployment = json.loads(k("get", "deployment", "learningsteps-api", "-n", NS, "-o", "json"))
    hpa = json.loads(k("get", "hpa", "learningsteps-api", "-n", NS, "-o", "json"))
    pods = json.loads(k("get", "pods", "-n", NS, "-l", "app=learningsteps-api", "-o", "json"))["items"]
    cpu = next((m.get("resource", {}).get("current", {}).get("averageUtilization")
                for m in hpa.get("status", {}).get("currentMetrics", [])
                if m.get("resource", {}).get("name") == "cpu"), None)
    return {
        "at": datetime.now(timezone.utc).isoformat(),
        "desired_replicas": deployment["spec"]["replicas"],
        "ready_replicas": sum(ready(pod) for pod in pods),
        "cpu_percent_of_request": cpu,
        "hpa_desired_replicas": hpa.get("status", {}).get("desiredReplicas"),
    }, deployment, hpa


def main():
    context = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, timeout=10)
    if context.returncode or context.stdout.strip() != "aks-learningsteps-evolution":
        raise RuntimeError("Expected LearningSteps AKS context")
    baseline, deployment, hpa = sample()
    spec = hpa["spec"]
    if (spec.get("minReplicas") != 2 or spec.get("maxReplicas") != 4
            or spec["scaleTargetRef"]["name"] != "learningsteps-api"
            or baseline["desired_replicas"] != 2 or baseline["ready_replicas"] != 2
            or baseline["cpu_percent_of_request"] is None
            or deployment.get("status", {}).get("updatedReplicas") != 2):
        raise RuntimeError("Need stable two-pod API and HPA 2..4 with CPU measurements")
    image = next(c["image"] for c in deployment["spec"]["template"]["spec"]["containers"]
                 if c["name"] == "api")
    if not re.fullmatch(r"acrlearningstepsalex0ad5f630\.azurecr\.io/learningsteps-api@sha256:[a-f0-9]{64}", image):
        raise RuntimeError("Expected immutable LearningSteps ACR image")
    job_name = "learningsteps-hpa-check-" + uuid4().hex[:8]
    manifest = {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": job_name, "namespace": NS},
        "spec": {"parallelism": 2, "completions": 2, "backoffLimit": 0,
                 "activeDeadlineSeconds": 330, "ttlSecondsAfterFinished": 600,
                 "template": {"metadata": {"labels": {"app": "learningsteps-hpa-load"}},
                              "spec": {
                                  "restartPolicy": "Never", "automountServiceAccountToken": False,
                                  "securityContext": {"runAsNonRoot": True, "runAsUser": 10001,
                                                      "seccompProfile": {"type": "RuntimeDefault"}},
                                  "containers": [{"name": "load", "image": image,
                                                  "command": ["python", "-c", LOAD],
                                                  "securityContext": {"readOnlyRootFilesystem": True,
                                                                      "allowPrivilegeEscalation": False,
                                                                      "capabilities": {"drop": ["ALL"]}},
                                                  "resources": {"requests": {"cpu": "100m", "memory": "64Mi"},
                                                                "limits": {"cpu": "500m", "memory": "128Mi"}}}]}}},
    }
    body = json.dumps(manifest)
    k("create", "--dry-run=server", "-f", "-", body=body)
    evidence = {"started_at": baseline["at"], "job": job_name, "image": image,
                "endpoint": "GET /health/live", "samples": [baseline],
                "scaled_up": False, "returned_to_two": False, "load_reports": [],
                "note_write_commands_executed": False, "hpa_configuration_changed": False}
    created = False
    try:
        k("create", "-f", "-", body=body)
        created = True
        print("Load started: two restricted generators; only GET /health/live", flush=True)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            time.sleep(15)
            current, _, _ = sample()
            evidence["samples"].append(current)
            print("Under load: ready={ready_replicas}, desired={desired_replicas}, CPU={cpu_percent_of_request}%".format(**current), flush=True)
            if current["ready_replicas"] >= 3 and (current["hpa_desired_replicas"] or 0) >= 3:
                evidence["scaled_up"] = True
                break
        load_pods = json.loads(k("get", "pods", "-n", NS, "-l", "job-name=" + job_name, "-o", "json"))["items"]
        for pod in load_pods:
            logs = k("logs", pod["metadata"]["name"], "-n", NS, "--tail=1")
            if logs:
                evidence["load_reports"].append(json.loads(logs))
    finally:
        try:
            if created:
                k("delete", "job", job_name, "-n", NS, "--wait=true", "--timeout=20s")
                print("Load removed. Waiting for HPA return to two (up to 7 minutes)...", flush=True)
                deadline = time.monotonic() + 420
                stable = 0
                while time.monotonic() < deadline:
                    current, _, _ = sample()
                    evidence["samples"].append(current)
                    print("After load: ready={ready_replicas}, desired={desired_replicas}, CPU={cpu_percent_of_request}%".format(**current), flush=True)
                    stable = stable + 1 if current["ready_replicas"] == current["desired_replicas"] == 2 else 0
                    if stable >= 2:
                        evidence["returned_to_two"] = True
                        break
                    time.sleep(15)
        finally:
            target = Path(__file__).resolve().parents[2] / "artifacts/azure/hpa-scaling-check.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            print("Evidence: artifacts/azure/hpa-scaling-check.json", flush=True)
    if not evidence["scaled_up"] or not evidence["returned_to_two"]:
        raise RuntimeError("Both scaling directions were not demonstrated; inspect saved samples")
    if sum(report.get("http_200", 0) for report in evidence["load_reports"]) < 100:
        raise RuntimeError("Insufficient successful HTTP requests recorded to accept this load test")
    print("PASS: successful HTTP load, HPA scale-up and return to two Ready API pods")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit("STOP: " + (str(error) if isinstance(error, RuntimeError)
                                     else "Kubernetes request timed out")) from None
