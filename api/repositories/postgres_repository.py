import json
import os
import uuid
import asyncpg
from datetime import datetime, timezone
from typing import Any, Dict, List
from dotenv import load_dotenv
from repositories.interface_repository import DatabaseInterface
from security.identity import Principal

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing")

class PostgresDB(DatabaseInterface):
    def __init__(self, owner: Principal):
        self.owner_tenant_id = uuid.UUID(owner.tenant_id)
        self.owner_object_id = uuid.UUID(owner.object_id)

    @staticmethod
    def datetime_serialize(obj):
        """Convert datetime objects to ISO format for JSON serialization."""
        if isinstance(obj, datetime):
                return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
        
    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.pool.close()

    async def create_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            query = """
            INSERT INTO entries (id, data, created_at, updated_at, owner_tenant_id, owner_object_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """
            entry_id = entry_data.get("id") or str(uuid.uuid4())
            data_json = json.dumps(entry_data, default=PostgresDB.datetime_serialize)
            
            row = await conn.fetchrow(
                query, 
                entry_id, 
                data_json, 
                entry_data["created_at"], 
                entry_data["updated_at"],
                self.owner_tenant_id,
                self.owner_object_id,
            )
            
            # Return a clean entry format without duplication
            if row:
                data = json.loads(row["data"])
                return {
                    "id": row["id"],
                    "work": data.get("work", ""),
                    "struggle": data.get("struggle", ""),
                    "intention": data.get("intention", ""),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return {}

    async def get_all_entries(self) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            query = """SELECT * FROM entries
                       WHERE owner_tenant_id = $1 AND owner_object_id = $2
                       ORDER BY created_at, id"""
            rows = await conn.fetch(query, self.owner_tenant_id, self.owner_object_id)
            entries = []
            for row in rows:
                data = json.loads(row["data"])
                entries.append({
                    "id": row["id"],
                    "work": data.get("work", ""),
                    "struggle": data.get("struggle", ""),
                    "intention": data.get("intention", ""),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            return entries
        
    async def get_entry(self, entry_id: str) -> Dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            query = """SELECT * FROM entries WHERE id = $1
                       AND owner_tenant_id = $2 AND owner_object_id = $3"""
            row = await conn.fetchrow(query, entry_id, self.owner_tenant_id, self.owner_object_id)
            
            if row:
                data = json.loads(row["data"])
                return {
                    "id": row["id"],
                    "work": data.get("work", ""),
                    "struggle": data.get("struggle", ""),
                    "intention": data.get("intention", ""),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None
   
    async def update_entry(self, entry_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any] | None:
        updated_at = datetime.now(timezone.utc)
        changes = {
            **{key: value for key, value in updated_data.items() if key in {"work", "struggle", "intention"}},
            "updated_at": updated_at,
        }
        data_json = json.dumps(changes, default=PostgresDB.datetime_serialize)

        async with self.pool.acquire() as conn:
            query = """
            UPDATE entries 
            SET data = data || $2::jsonb, updated_at = $3
            WHERE id = $1 AND owner_tenant_id = $4 AND owner_object_id = $5
            RETURNING *
            """
            row = await conn.fetchrow(
                query, entry_id, data_json, updated_at,
                self.owner_tenant_id, self.owner_object_id,
            )
            if row is None:
                return None
            data = json.loads(row["data"])
            return {
                "id": row["id"],
                "work": data.get("work", ""),
                "struggle": data.get("struggle", ""),
                "intention": data.get("intention", ""),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    async def delete_entry(self, entry_id: str) -> bool:
        async with self.pool.acquire() as conn:
            query = """DELETE FROM entries WHERE id = $1
                       AND owner_tenant_id = $2 AND owner_object_id = $3 RETURNING id"""
            return await conn.fetchval(
                query, entry_id, self.owner_tenant_id, self.owner_object_id
            ) is not None

    async def delete_all_entries(self) -> None:
        async with self.pool.acquire() as conn:
            query = "DELETE FROM entries WHERE owner_tenant_id = $1 AND owner_object_id = $2"
            await conn.execute(query, self.owner_tenant_id, self.owner_object_id)
