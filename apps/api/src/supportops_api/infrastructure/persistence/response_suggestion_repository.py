from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.response_suggestions import ResponseSuggestionRepository
from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
    SuggestedResponseConfidenceLevel,
    SuggestedResponseStatus,
)
from supportops_api.infrastructure.persistence.models import SuggestedResponseRecord


class PostgresResponseSuggestionRepository(ResponseSuggestionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, suggestion: SuggestedResponse) -> None:
        self._session.add(_suggestion_to_record(suggestion))
        await self._session.flush()

    async def save(self, suggestion: SuggestedResponse) -> None:
        record = await self._session.get(SuggestedResponseRecord, suggestion.id)
        if record is None:
            self._session.add(_suggestion_to_record(suggestion))
        else:
            _update_suggestion_record(record, suggestion)

        await self._session.flush()

    async def get(self, suggestion_id: UUID) -> SuggestedResponse | None:
        record = await self._session.get(SuggestedResponseRecord, suggestion_id)
        if record is None:
            return None

        return _record_to_suggestion(record)

    async def list_for_ticket(self, ticket_id: UUID) -> list[SuggestedResponse]:
        result = await self._session.execute(
            select(SuggestedResponseRecord)
            .where(SuggestedResponseRecord.ticket_id == ticket_id)
            .order_by(SuggestedResponseRecord.created_at.desc())
        )
        return [_record_to_suggestion(record) for record in result.scalars()]


def _suggestion_to_record(suggestion: SuggestedResponse) -> SuggestedResponseRecord:
    return SuggestedResponseRecord(
        id=suggestion.id,
        ticket_id=suggestion.ticket_id,
        content=suggestion.content,
        status=suggestion.status.value,
        sources=suggestion.sources,
        confidence_score=suggestion.confidence_score,
        confidence_level=suggestion.confidence_level.value,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


def _update_suggestion_record(
    record: SuggestedResponseRecord, suggestion: SuggestedResponse
) -> None:
    record.ticket_id = suggestion.ticket_id
    record.content = suggestion.content
    record.status = suggestion.status.value
    record.sources = suggestion.sources
    record.confidence_score = suggestion.confidence_score
    record.confidence_level = suggestion.confidence_level.value
    record.created_at = suggestion.created_at
    record.updated_at = suggestion.updated_at


def _record_to_suggestion(record: SuggestedResponseRecord) -> SuggestedResponse:
    sources = record.sources if isinstance(record.sources, list) else []
    return SuggestedResponse(
        id=record.id,
        ticket_id=record.ticket_id,
        content=record.content,
        status=SuggestedResponseStatus(record.status),
        sources=sources,
        confidence_score=record.confidence_score,
        confidence_level=SuggestedResponseConfidenceLevel(record.confidence_level),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
