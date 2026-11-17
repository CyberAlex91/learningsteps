from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends

from models.summary import SummaryRequest, SummaryResponse
from routers.journal_router import get_entry_service
from security.dependencies import current_user
from security.identity import Principal
from services.entry_service import EntryService
from services.summary_service import FoundrySummarizer, SummaryLimiter, notes_payload

router = APIRouter(tags=["KI-Zusammenfassung"])
_limiter = SummaryLimiter()


def get_summarizer() -> FoundrySummarizer:
    return FoundrySummarizer()


def get_limiter() -> SummaryLimiter:
    return _limiter


@router.post("/me/notes/summary", response_model=SummaryResponse)
async def summarize_my_notes(
    request: SummaryRequest | None = Body(default=None),
    user: Principal = Depends(current_user),
    entry_service: EntryService = Depends(get_entry_service),
    summarizer: FoundrySummarizer = Depends(get_summarizer),
    limiter: SummaryLimiter = Depends(get_limiter),
):
    """Alle gespeicherten eigenen Notizen zusammenfassen; keine Nutzerauswahl im Body."""
    notes = await entry_service.get_all_entries()
    if not notes:
        return SummaryResponse(
            summary="Du hast noch keine zugeordneten Notizen. Lege zuerst eigene Eintraege an.",
            note_count=0,
            ai_generated=False,
            generated_at=datetime.now(timezone.utc),
        )
    notes_payload(notes)  # Fail explicitly before reserving quota or invoking Azure.
    limiter.reserve(user)
    text = await summarizer.summarize(notes)
    return SummaryResponse(
        summary=text,
        note_count=len(notes),
        ai_generated=True,
        generated_at=datetime.now(timezone.utc),
    )
