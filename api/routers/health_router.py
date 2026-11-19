"""Unauthenticated probe results contain no configuration or database details."""

import asyncio
import asyncpg
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from repositories.postgres_repository import DATABASE_URL

router = APIRouter()


@router.get("/health/live", include_in_schema=False)
async def live():
    return {"status": "alive"}


@router.get("/health/ready", include_in_schema=False)
async def ready():
    connection = None
    try:
        async with asyncio.timeout(3):
            connection = await asyncpg.connect(DATABASE_URL, timeout=2, command_timeout=2)
            # Also checks the application's table exists and the role can read it.
            await connection.fetchval("SELECT 1 FROM public.entries LIMIT 1")
    except Exception:
        # Never return exception text, host, credentials, SQL or note contents.
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    finally:
        if connection is not None:
            # terminate() is immediate: cleanup must not make the probe hang.
            connection.terminate()
    return {"status": "ready"}
