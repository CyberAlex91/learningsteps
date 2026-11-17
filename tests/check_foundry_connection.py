"""Explicit live SDK smoke test; synthetic RAM-only input, never stored notes."""

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from services.summary_service import FoundrySummarizer  # noqa: E402


async def run():
    topics = [
        ("Terraform State und Locking geuebt", "Gleichzeitige Aenderungen am State", "Remote State testen"),
        ("Kubernetes Readiness und Liveness verglichen", "Unterschied der beiden Probes", "Readiness-Probe konfigurieren"),
        ("JWT-Signatur und Audience geprueft", "ID-Token von Access-Token unterscheiden", "Nutzerrechte testen"),
    ]
    notes = [
        dict(id=str(uuid4()), work=w, struggle=s, intention=i)
        for w, s, i in topics
    ]
    text = await FoundrySummarizer().summarize(notes)
    return {"success": True, "runtime": "development-container", "credential": "AzureCliCredential",
            "syntheticNoteCount": len(notes), "storedNotesUsed": False, "summary": text}


if __name__ == "__main__":
    try:
        result = asyncio.run(run())
    except HTTPException as error:
        print(json.dumps({"success": False, "status": error.status_code, "detail": error.detail}))
        sys.exit(1)
    except Exception as error:
        print(json.dumps({"success": False, "errorType": type(error).__name__}))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
