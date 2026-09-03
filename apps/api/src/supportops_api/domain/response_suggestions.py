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


class SuggestedResponseConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class SuggestedResponse:
    ticket_id: UUID
    content: str
    id: UUID = field(default_factory=uuid4)
    status: SuggestedResponseStatus = SuggestedResponseStatus.DRAFT
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence_score: float | None = None
    confidence_level: SuggestedResponseConfidenceLevel = SuggestedResponseConfidenceLevel.LOW
    confidence_reason: str = "No trusted knowledge sources were retrieved for this ticket."
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        self.confidence_reason = self.confidence_reason.strip()

        if not self.content:
            raise ValueError("Suggested response content is required")

        if not self.confidence_reason:
            raise ValueError("Suggested response confidence reason is required")

        if self.confidence_score is not None and not 0 <= self.confidence_score <= 1:
            raise ValueError("Suggested response confidence score must be between 0 and 1")

    @classmethod
    def create(
        cls,
        *,
        ticket_id: UUID,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        confidence_score: float | None = None,
        confidence_level: SuggestedResponseConfidenceLevel = SuggestedResponseConfidenceLevel.LOW,
        confidence_reason: str = "No trusted knowledge sources were retrieved for this ticket.",
    ) -> SuggestedResponse:
        return cls(
            ticket_id=ticket_id,
            content=content,
            sources=sources or [],
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            confidence_reason=confidence_reason,
        )

    def approve(self) -> None:
        self.status = SuggestedResponseStatus.APPROVED
        self.updated_at = _utcnow()

    def reject(self) -> None:
        self.status = SuggestedResponseStatus.REJECTED
        self.updated_at = _utcnow()
