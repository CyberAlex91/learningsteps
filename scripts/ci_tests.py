# Zweck: Führt CI-Tests ausschließlich gegen die vorgesehene isolierte Testdatenbank aus.
"""CI-only test orchestration; refuses any non-disposable database target."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

import asyncpg

ROOT = Path(__file__).resolve().parents[1]


async def initialize_disposable_database(dsn):
    connection = await asyncpg.connect(dsn, timeout=10)
    try:
        sql = (ROOT / "database_setup.sql").read_text(encoding="utf-8-sig")
        sql = "\n".join(line for line in sql.splitlines() if line.strip() != r"\d entries;")
        if any(line.lstrip().startswith("\\") for line in sql.splitlines()):
            raise RuntimeError("Unexpected psql command in CI schema")
        await connection.execute(sql)
    finally:
        await connection.close()


def main():
    dsn = os.environ.get("DATABASE_URL", "")
    target = urlsplit(dsn)
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or target.hostname != "127.0.0.1" or target.port != 5432
            or target.username != "ci" or target.path != "/learningsteps_ci"
            or os.environ.get("DATABASE_URL_FILE")):
        raise SystemExit("STOP: this helper only accepts the disposable GitHub CI database")
    for pattern in ("test_identity.py", "test_summary.py", "test_runtime.py", "test_ci_delivery.py", "test_lifecycle.py"):
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                        "-p", pattern, "-v"], cwd=ROOT, check=True)
    asyncio.run(initialize_disposable_database(dsn))
    subprocess.run([sys.executable, "tests/test_notes_isolation.py"], cwd=ROOT, check=True)
    print("PASS: offline unit tests and real PostgreSQL user-isolation checks")


if __name__ == "__main__":
    main()
