from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class SuggestedResponseStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class SuggestedResponse:
    ticket_id: UUID
    content: str
    id: UUID = field(default_factory=uuid4)
    status: SuggestedResponseStatus = SuggestedResponseStatus.DRAFT
    sources: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.content = self.content.strip()

        if not self.content:
            raise ValueError("Suggested response content is required")

    @classmethod
    def create(
        cls,
        *,
        ticket_id: UUID,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> SuggestedResponse:
        return cls(ticket_id=ticket_id, content=content, sources=sources or [])

    def approve(self) -> None:
        self.status = SuggestedResponseStatus.APPROVED
        self.updated_at = _utcnow()

    def reject(self) -> None:
        self.status = SuggestedResponseStatus.REJECTED
        self.updated_at = _utcnow()
