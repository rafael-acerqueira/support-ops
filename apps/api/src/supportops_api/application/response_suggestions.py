from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from supportops_api.application.tickets import TicketNotFoundError, TicketRepository
from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
    SuggestedResponseConfidenceLevel,
)
from supportops_api.domain.tickets import Ticket


class SuggestedResponseNotFoundError(Exception):
    def __init__(self, suggestion_id: UUID) -> None:
        super().__init__(f"Suggested response not found: {suggestion_id}")
        self.suggestion_id = suggestion_id


class ResponseGenerationProviderError(Exception):
    pass


class ResponseSuggestionRepository(Protocol):
    async def add(self, suggestion: SuggestedResponse) -> None:
        pass

    async def save(self, suggestion: SuggestedResponse) -> None:
        pass

    async def get(self, suggestion_id: UUID) -> SuggestedResponse | None:
        pass

    async def list_for_ticket(self, ticket_id: UUID) -> list[SuggestedResponse]:
        pass


@dataclass(frozen=True)
class GeneratedSuggestedResponse:
    content: str
    sources: list[dict[str, Any]]
    confidence_score: float | None = None
    confidence_level: SuggestedResponseConfidenceLevel = SuggestedResponseConfidenceLevel.LOW
    confidence_reason: str = "No trusted knowledge sources were retrieved for this ticket."


@dataclass(frozen=True)
class RetrievedKnowledgeSource:
    document_id: UUID
    document_name: str
    document_type: str
    chunk_id: UUID
    chunk_index: int
    content: str
    relevance_score: float


@dataclass(frozen=True)
class KnowledgeChunkCandidate:
    document_id: UUID
    document_name: str
    document_type: str
    product_area: str
    tags: tuple[str, ...]
    chunk_id: UUID
    chunk_index: int
    content: str


class KnowledgeSourceRepository(Protocol):
    async def list_indexed_chunks(self, *, limit: int = 50) -> list[KnowledgeChunkCandidate]:
        pass

    async def search_similar_chunks(
        self,
        *,
        embedding: tuple[float, ...],
        limit: int = 3,
    ) -> list[RetrievedKnowledgeSource]:
        pass


class TicketKnowledgeRetriever(Protocol):
    async def retrieve(self, ticket: Ticket, *, limit: int = 3) -> list[RetrievedKnowledgeSource]:
        pass


def confidence_level_for_score(score: float | None) -> SuggestedResponseConfidenceLevel:
    if score is None:
        return SuggestedResponseConfidenceLevel.LOW

    if score >= 0.75:
        return SuggestedResponseConfidenceLevel.HIGH

    if score >= 0.5:
        return SuggestedResponseConfidenceLevel.MEDIUM

    return SuggestedResponseConfidenceLevel.LOW


def confidence_score_from_sources(
    sources: list[RetrievedKnowledgeSource],
) -> float | None:
    if not sources:
        return None

    return max(source.relevance_score for source in sources)


def confidence_reason_from_sources(
    sources: list[RetrievedKnowledgeSource],
) -> str:
    if not sources:
        return "No trusted knowledge sources were retrieved for this ticket."

    best_source = max(sources, key=lambda source: source.relevance_score)
    score_percent = round(best_source.relevance_score * 100)
    return (
        f"Best retrieved source matched this ticket with {score_percent}% relevance "
        f"from {best_source.document_name}."
    )


class ResponseSuggestionGenerator(Protocol):
    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        pass


@dataclass(frozen=True)
class GenerateSuggestedResponseInput:
    ticket_id: UUID


class GenerateSuggestedResponse:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        suggestion_repository: ResponseSuggestionRepository,
        generator: ResponseSuggestionGenerator,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._suggestion_repository = suggestion_repository
        self._generator = generator

    async def execute(self, data: GenerateSuggestedResponseInput) -> SuggestedResponse:
        ticket = await self._ticket_repository.get(data.ticket_id)
        if ticket is None:
            raise TicketNotFoundError(data.ticket_id)

        generated_response = await self._generator.generate(ticket)
        suggestion = SuggestedResponse.create(
            ticket_id=ticket.id,
            content=generated_response.content,
            sources=generated_response.sources,
            confidence_score=generated_response.confidence_score,
            confidence_level=generated_response.confidence_level,
            confidence_reason=generated_response.confidence_reason,
        )
        await self._suggestion_repository.add(suggestion)
        return suggestion


class ListSuggestedResponses:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        suggestion_repository: ResponseSuggestionRepository,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._suggestion_repository = suggestion_repository

    async def execute(self, ticket_id: UUID) -> list[SuggestedResponse]:
        ticket = await self._ticket_repository.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)

        return await self._suggestion_repository.list_for_ticket(ticket_id)


class ApproveSuggestedResponse:
    def __init__(self, repository: ResponseSuggestionRepository) -> None:
        self._repository = repository

    async def execute(self, ticket_id: UUID, suggestion_id: UUID) -> SuggestedResponse:
        suggestion = await self._repository.get(suggestion_id)
        if suggestion is None or suggestion.ticket_id != ticket_id:
            raise SuggestedResponseNotFoundError(suggestion_id)

        suggestion.approve()
        await self._repository.save(suggestion)
        return suggestion


class RejectSuggestedResponse:
    def __init__(self, repository: ResponseSuggestionRepository) -> None:
        self._repository = repository

    async def execute(self, ticket_id: UUID, suggestion_id: UUID) -> SuggestedResponse:
        suggestion = await self._repository.get(suggestion_id)
        if suggestion is None or suggestion.ticket_id != ticket_id:
            raise SuggestedResponseNotFoundError(suggestion_id)

        suggestion.reject()
        await self._repository.save(suggestion)
        return suggestion
