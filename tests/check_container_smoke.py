"""Run through stdin inside the production image; no database or Azure access."""

import json
import os
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(path, method="GET"):
    data = b"{}" if method == "POST" else None
    req = Request(
        "http://127.0.0.1:8765" + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=2) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def main():
    if os.getuid() != 10001:
        raise RuntimeError("Expected non-root UID 10001")
    # A deliberately unusable synthetic DSN: authenticated database work is
    # outside this smoke test. No production secrets or login are provided.
    os.environ["DATABASE_URL"] = "postgresql://smoke:synthetic@127.0.0.1:1/smoke"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", "8765", "--no-access-log", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while True:
            if process.poll() is not None:
                raise RuntimeError("API exited during startup")
            try:
                status, body = request("/openapi.json")
                break
            except (URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("API startup timed out") from None
                time.sleep(0.2)

        if status != 200:
            raise RuntimeError("OpenAPI did not return HTTP 200")
        schema = json.loads(body)
        if "post" not in schema["paths"].get("/me/notes/summary", {}):
            raise RuntimeError("Summary endpoint absent")
        if not schema["components"]["securitySchemes"]:
            raise RuntimeError("Authentication schema absent")
        print("PASS: non-root API startup, OpenAPI and summary route")
        for path, method, expected in (
            ("/docs", "GET", 200),
            ("/health/live", "GET", 200),
            ("/health/ready", "GET", 503),
            ("/me", "GET", 401),
            ("/entries", "GET", 401),
            ("/me/notes/summary", "POST", 401),
        ):
            actual, _ = request(path, method)
            if actual != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, got {actual}")
            print(f"PASS: {method} {path} -> {actual}")
        print("SUCCESS: image smoke test; no database or model call required")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
