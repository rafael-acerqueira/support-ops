from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from supportops_api.application.tickets import TicketNotFoundError, TicketRepository
from supportops_api.domain.response_suggestions import SuggestedResponse
from supportops_api.domain.tickets import Ticket


class SuggestedResponseNotFoundError(Exception):
    def __init__(self, suggestion_id: UUID) -> None:
        super().__init__(f"Suggested response not found: {suggestion_id}")
        self.suggestion_id = suggestion_id


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


@dataclass(frozen=True)
class RetrievedKnowledgeSource:
    document_id: UUID
    document_name: str
    document_type: str
    chunk_id: UUID
    chunk_index: int
    content: str
    relevance_score: float


class TicketKnowledgeRetriever(Protocol):
    async def retrieve(self, ticket: Ticket, *, limit: int = 3) -> list[RetrievedKnowledgeSource]:
        pass


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
