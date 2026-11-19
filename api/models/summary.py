# Zweck: Definiert das Antwortformat einer KI-Zusammenfassung.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SummaryRequest(BaseModel):
    """No client-supplied notes, owner, endpoint or prompt is accepted."""

    model_config = ConfigDict(extra="forbid")


class SummaryResponse(BaseModel):
    summary: str = Field(max_length=16_000)
    note_count: int = Field(ge=0)
    ai_generated: bool
    generated_at: datetime
