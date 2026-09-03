from uuid import UUID, uuid4

import pytest

from supportops_api.application.response_suggestions import (
    ApproveSuggestedResponse,
    GeneratedSuggestedResponse,
    GenerateSuggestedResponse,
    GenerateSuggestedResponseInput,
    ListSuggestedResponses,
    RejectSuggestedResponse,
    SuggestedResponseNotFoundError,
)
from supportops_api.application.tickets import TicketNotFoundError
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
    SuggestedResponseConfidenceLevel,
    SuggestedResponseStatus,
)
from supportops_api.domain.tickets import Ticket


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self.tickets: dict[UUID, Ticket] = {}

    async def add(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket

    async def save(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return self.tickets.get(ticket_id)

    async def list_all(self) -> list[Ticket]:
        return list(self.tickets.values())


class InMemorySuggestionRepository:
    def __init__(self) -> None:
        self.suggestions: dict[UUID, SuggestedResponse] = {}
        self.saved_suggestions: list[SuggestedResponse] = []

    async def add(self, suggestion: SuggestedResponse) -> None:
        self.suggestions[suggestion.id] = suggestion

    async def save(self, suggestion: SuggestedResponse) -> None:
        self.suggestions[suggestion.id] = suggestion
        self.saved_suggestions.append(suggestion)

    async def get(self, suggestion_id: UUID) -> SuggestedResponse | None:
        return self.suggestions.get(suggestion_id)

    async def list_for_ticket(self, ticket_id: UUID) -> list[SuggestedResponse]:
        return [
            suggestion
            for suggestion in self.suggestions.values()
            if suggestion.ticket_id == ticket_id
        ]


class FakeGenerator:
    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        return GeneratedSuggestedResponse(
            content=f"Suggested reply for {ticket.external_id}",
            sources=[{"document_name": "billing-playbook.md", "relevance_score": 0.9}],
            confidence_score=0.9,
            confidence_level=SuggestedResponseConfidenceLevel.HIGH,
        )


def create_ticket() -> Ticket:
    return Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Billing export failed",
        description="Customer cannot export invoices.",
        product_area=ProductArea.BILLING,
    )


@pytest.mark.asyncio
async def test_generate_suggested_response_persists_draft() -> None:
    ticket_repository = InMemoryTicketRepository()
    suggestion_repository = InMemorySuggestionRepository()
    ticket = create_ticket()
    await ticket_repository.add(ticket)

    suggestion = await GenerateSuggestedResponse(
        ticket_repository, suggestion_repository, FakeGenerator()
    ).execute(GenerateSuggestedResponseInput(ticket_id=ticket.id))

    assert suggestion.content == "Suggested reply for TCK-1001"
    assert suggestion.status == SuggestedResponseStatus.DRAFT
    assert suggestion.sources == [{"document_name": "billing-playbook.md", "relevance_score": 0.9}]
    assert suggestion.confidence_score == 0.9
    assert suggestion.confidence_level == SuggestedResponseConfidenceLevel.HIGH
    assert suggestion_repository.suggestions[suggestion.id] == suggestion


@pytest.mark.asyncio
async def test_generate_suggested_response_requires_existing_ticket() -> None:
    with pytest.raises(TicketNotFoundError):
        await GenerateSuggestedResponse(
            InMemoryTicketRepository(), InMemorySuggestionRepository(), FakeGenerator()
        ).execute(GenerateSuggestedResponseInput(ticket_id=uuid4()))


@pytest.mark.asyncio
async def test_list_suggested_responses_requires_existing_ticket() -> None:
    with pytest.raises(TicketNotFoundError):
        await ListSuggestedResponses(
            InMemoryTicketRepository(), InMemorySuggestionRepository()
        ).execute(uuid4())


@pytest.mark.asyncio
async def test_approve_and_reject_suggested_response() -> None:
    repository = InMemorySuggestionRepository()
    suggestion = SuggestedResponse.create(ticket_id=uuid4(), content="Draft reply")
    await repository.add(suggestion)

    approved = await ApproveSuggestedResponse(repository).execute(
        suggestion.ticket_id, suggestion.id
    )
    assert approved.status == SuggestedResponseStatus.APPROVED

    rejected = await RejectSuggestedResponse(repository).execute(
        suggestion.ticket_id, suggestion.id
    )
    assert rejected.status == SuggestedResponseStatus.REJECTED
    assert repository.saved_suggestions == [suggestion, suggestion]


@pytest.mark.asyncio
async def test_approve_rejects_wrong_ticket_id() -> None:
    repository = InMemorySuggestionRepository()
    suggestion = SuggestedResponse.create(ticket_id=uuid4(), content="Draft reply")
    await repository.add(suggestion)

    with pytest.raises(SuggestedResponseNotFoundError):
        await ApproveSuggestedResponse(repository).execute(uuid4(), suggestion.id)
