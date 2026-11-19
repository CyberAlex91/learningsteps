"""Remove one healthy API pod and verify controller replacement; no note writes."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

NAMESPACE = "learningsteps"


def kubectl(*args):
    result = subprocess.run(
        ["kubectl", *args, "--request-timeout=20s"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Kubernetes request failed; inspect cluster access/status")
    return result.stdout.strip()


def pods():
    return json.loads(kubectl("get", "pods", "-n", NAMESPACE,
                              "-l", "app=learningsteps-api", "-o", "json"))["items"]


def ready(pod):
    return not pod["metadata"].get("deletionTimestamp") and any(
        condition["type"] == "Ready" and condition["status"] == "True"
        for condition in pod.get("status", {}).get("conditions", [])
    )


def main():
    # This helper intentionally permits exactly one delete, after all guards.
    context = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, timeout=10)
    if context.returncode or context.stdout.strip() != "aks-learningsteps-evolution":
        raise RuntimeError("Expected LearningSteps AKS context")
    deployment = json.loads(kubectl("get", "deployment", "learningsteps-api",
                                   "-n", NAMESPACE, "-o", "json"))
    before = pods()
    desired = deployment["spec"]["replicas"]
    status = deployment.get("status", {})
    if (desired < 2 or status.get("observedGeneration", 0) < deployment["metadata"]["generation"]
            or status.get("updatedReplicas") != desired
            or len(before) != desired or not all(ready(pod) for pod in before)):
        raise RuntimeError("Need a stable deployment with at least two Ready pods; retry after CI rollout")
    victim = before[0]["metadata"]
    old_uids = {pod["metadata"]["uid"] for pod in before}
    survivor_uids = old_uids - {victim["uid"]}
    started = time.monotonic()
    print("Removing one API pod: " + victim["name"], flush=True)
    kubectl("delete", "pod", victim["name"], "-n", NAMESPACE, "--wait=false")
    print("Waiting for a new Ready replacement (up to 180 seconds)...", flush=True)
    deadline = started + 180
    while time.monotonic() < deadline:
        after = pods()
        active_ready = [pod for pod in after if ready(pod)]
        new = [pod for pod in active_ready if pod["metadata"]["uid"] not in old_uids]
        uids = {pod["metadata"]["uid"] for pod in active_ready}
        if new and len(active_ready) >= desired and survivor_uids.issubset(uids):
            evidence = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "deleted_pod": victim["name"], "deleted_uid": victim["uid"],
                "replacement_pod": new[0]["metadata"]["name"],
                "replacement_uid": new[0]["metadata"]["uid"],
                "ready_replicas": len(active_ready),
                "recovery_seconds": round(time.monotonic() - started, 1),
                "other_original_pods_ready_at_completion": True,
                "note_write_commands_executed": False,
                "continuous_availability_measured": False,
            }
            target = Path(__file__).resolve().parents[2] / "artifacts/azure/pod-recovery-check.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            print("PASS: new pod UID and Ready replacement; other original pods remain Ready")
            print("Recovery seconds: " + str(evidence["recovery_seconds"]))
            print("Evidence: artifacts/azure/pod-recovery-check.json")
            return
        time.sleep(5)
    raise RuntimeError("Replacement not verified within 180s; no second pod was deleted")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit("STOP: " + (str(error) if isinstance(error, RuntimeError)
                                     else "Kubernetes request timed out")) from None
