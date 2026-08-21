from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from supportops_api.domain.response_suggestions import SuggestedResponse, SuggestedResponseStatus


class SuggestedResponseResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    content: str
    status: SuggestedResponseStatus
    sources: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, suggestion: SuggestedResponse) -> SuggestedResponseResponse:
        return cls(
            id=suggestion.id,
            ticket_id=suggestion.ticket_id,
            content=suggestion.content,
            status=suggestion.status,
            sources=suggestion.sources,
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at,
        )
