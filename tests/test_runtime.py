"""Offline checks of secret-file configuration and probe failure behavior."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from database_config import get_database_url

# Synthetic configuration only. Tests never connect to Azure or a real database.
os.environ["DATABASE_URL"] = "postgresql://synthetic:synthetic@127.0.0.1:1/test"
os.environ.pop("DATABASE_URL_FILE", None)
from main import app


class DatabaseConfigTests(unittest.TestCase):
    def test_local_environment_supported(self):
        self.assertEqual(get_database_url({"DATABASE_URL": "synthetic-dsn"}), "synthetic-dsn")

    def test_mounted_file_and_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "database-url"
            path.write_text(" synthetic-dsn\n", encoding="utf-8")
            self.assertEqual(get_database_url({"DATABASE_URL_FILE": str(path)}), "synthetic-dsn")

    def test_ambiguous_sources_rejected(self):
        with self.assertRaisesRegex(ValueError, "only one"):
            get_database_url({"DATABASE_URL": "synthetic", "DATABASE_URL_FILE": "/other"})

    def test_missing_file_hides_path(self):
        with self.assertRaises(ValueError) as caught:
            get_database_url({"DATABASE_URL_FILE": "/missing/sensitive-name"})
        self.assertEqual(str(caught.exception), "Database credential file cannot be read")

    def test_empty_configuration_rejected(self):
        for source in ({}, {"DATABASE_URL": "   "}):
            with self.assertRaises(ValueError):
                get_database_url(source)


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(path)

    async def test_liveness_never_connects_to_database(self):
        with patch("routers.health_router.asyncpg.connect", new_callable=AsyncMock) as connect:
            response = await self.request("/health/live")
            self.assertEqual(response.status_code, 200)
            connect.assert_not_called()

    async def test_readiness_success_and_cleanup_with_empty_table(self):
        connection = MagicMock()
        connection.fetchval = AsyncMock(return_value=None)
        with patch("routers.health_router.asyncpg.connect", new_callable=AsyncMock, return_value=connection):
            response = await self.request("/health/ready")
        self.assertEqual(response.status_code, 200)
        connection.fetchval.assert_awaited_once()
        connection.terminate.assert_called_once()

    async def test_connection_failure_is_safe_503(self):
        with patch("routers.health_router.asyncpg.connect", new_callable=AsyncMock,
                   side_effect=OSError("secret-password-in-error")):
            response = await self.request("/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "not_ready"})

    async def test_missing_schema_is_not_ready_and_closes_connection(self):
        connection = MagicMock()
        connection.fetchval = AsyncMock(side_effect=RuntimeError("sensitive SQL error"))
        with patch("routers.health_router.asyncpg.connect", new_callable=AsyncMock, return_value=connection):
            response = await self.request("/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sensitive", response.text)
        connection.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
