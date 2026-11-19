# Zweck: Prüft ausdrücklich eine echte Foundry-Modellantwort ohne Tokenausgabe.
"""Explicit live SDK smoke test; synthetic RAM-only input, never stored notes."""

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

# A Kubernetes stdin execution already has /app on its import path.
source_file = globals().get("__file__", "")
if source_file and not source_file.startswith("<"):
    sys.path.insert(0, str(Path(source_file).resolve().parents[1] / "api"))
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
    summarizer = FoundrySummarizer()
    text = await summarizer.summarize(notes)
    mode = summarizer.credential_type
    return {"success": True, "runtime": "aks" if mode == "workload_identity" else "development-container",
            "credential": mode,
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
