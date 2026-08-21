from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio

from src.main import app
from supportops_api.api.dependencies import (
    get_response_suggestion_generator,
    get_response_suggestion_repository,
    get_ticket_repository,
)
from supportops_api.application.response_suggestions import (
    GeneratedSuggestedResponse,
    ResponseSuggestionRepository,
)
from supportops_api.application.tickets import TicketRepository
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.response_suggestions import SuggestedResponse, SuggestedResponseStatus
from supportops_api.domain.tickets import Ticket, TicketStatus
from supportops_api.infrastructure.database import get_session


class InMemoryResponseSuggestionRepository(ResponseSuggestionRepository):
    def __init__(self) -> None:
        self.suggestions: dict[UUID, SuggestedResponse] = {}

    async def add(self, suggestion: SuggestedResponse) -> None:
        self.suggestions[suggestion.id] = suggestion

    async def save(self, suggestion: SuggestedResponse) -> None:
        self.suggestions[suggestion.id] = suggestion

    async def get(self, suggestion_id: UUID) -> SuggestedResponse | None:
        return self.suggestions.get(suggestion_id)

    async def list_for_ticket(self, ticket_id: UUID) -> list[SuggestedResponse]:
        return [
            suggestion
            for suggestion in self.suggestions.values()
            if suggestion.ticket_id == ticket_id
        ]


class FakeResponseSuggestionGenerator:
    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        return GeneratedSuggestedResponse(
            content=f"Suggested reply for {ticket.external_id}",
            sources=[{"document_name": "billing-playbook.md", "relevance_score": 0.9}],
        )


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class InMemoryTicketRepository(TicketRepository):
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


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[
    tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ]
]:
    repository = InMemoryTicketRepository()
    suggestion_repository = InMemoryResponseSuggestionRepository()
    session = FakeSession()

    app.dependency_overrides[get_ticket_repository] = lambda: repository
    app.dependency_overrides[get_response_suggestion_repository] = lambda: suggestion_repository
    app.dependency_overrides[get_response_suggestion_generator] = (
        lambda: FakeResponseSuggestionGenerator()
    )
    app.dependency_overrides[get_session] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repository, suggestion_repository, session

    app.dependency_overrides.clear()


def create_ticket(repository: InMemoryTicketRepository) -> Ticket:
    ticket = Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Billing export failed",
        description="Customer cannot export invoices.",
        product_area=ProductArea.BILLING,
    )
    repository.tickets[ticket.id] = ticket
    return ticket


@pytest.mark.asyncio
async def test_create_ticket(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, _suggestion_repository, session = api_client

    response = await client.post(
        "/api/tickets",
        json={
            "external_id": " TCK-1001 ",
            "customer_name": " Acme Corp ",
            "customer_tier": " Enterprise ",
            "subject": " Billing export failed ",
            "description": " Customer cannot export invoices. ",
            "product_area": "billing",
            "priority": "high",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["external_id"] == "TCK-1001"
    assert body["customer_tier"] == "enterprise"
    assert body["status"] == "open"
    assert body["priority"] == "high"
    assert UUID(body["id"]) in repository.tickets
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_list_tickets(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, _suggestion_repository, _session = api_client
    ticket = create_ticket(repository)

    response = await client.get("/api/tickets")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(ticket.id)


@pytest.mark.asyncio
async def test_get_ticket(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, _suggestion_repository, _session = api_client
    ticket = create_ticket(repository)

    response = await client.get(f"/api/tickets/{ticket.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(ticket.id)


@pytest.mark.asyncio
async def test_get_ticket_returns_404(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, _repository, _suggestion_repository, _session = api_client
    ticket_id = uuid4()

    response = await client.get(f"/api/tickets/{ticket_id}")

    assert response.status_code == 404
    assert response.json()["detail"]["ticket_id"] == str(ticket_id)


@pytest.mark.asyncio
async def test_update_ticket_priority(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, _suggestion_repository, session = api_client
    ticket = create_ticket(repository)

    response = await client.patch(f"/api/tickets/{ticket.id}/priority", json={"priority": "urgent"})

    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"
    assert repository.tickets[ticket.id].priority == "urgent"
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_update_ticket_status(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, _suggestion_repository, session = api_client
    ticket = create_ticket(repository)

    response = await client.patch(f"/api/tickets/{ticket.id}/status", json={"status": "triaged"})

    assert response.status_code == 200
    assert response.json()["status"] == "triaged"
    assert repository.tickets[ticket.id].status == TicketStatus.TRIAGED
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_generate_suggested_response(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, suggestion_repository, session = api_client
    ticket = create_ticket(repository)

    response = await client.post(f"/api/tickets/{ticket.id}/suggested-responses")

    body = response.json()
    assert response.status_code == 201
    assert body["ticket_id"] == str(ticket.id)
    assert body["content"] == "Suggested reply for TCK-1001"
    assert body["status"] == "draft"
    assert body["sources"] == [{"document_name": "billing-playbook.md", "relevance_score": 0.9}]
    assert UUID(body["id"]) in suggestion_repository.suggestions
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_list_suggested_responses(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, suggestion_repository, _session = api_client
    ticket = create_ticket(repository)
    suggestion = SuggestedResponse.create(ticket_id=ticket.id, content="Draft reply")
    await suggestion_repository.add(suggestion)

    response = await client.get(f"/api/tickets/{ticket.id}/suggested-responses")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(suggestion.id)


@pytest.mark.asyncio
async def test_approve_suggested_response(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, suggestion_repository, session = api_client
    ticket = create_ticket(repository)
    suggestion = SuggestedResponse.create(ticket_id=ticket.id, content="Draft reply")
    await suggestion_repository.add(suggestion)

    response = await client.patch(
        f"/api/tickets/{ticket.id}/suggested-responses/{suggestion.id}/approve"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert (
        suggestion_repository.suggestions[suggestion.id].status == SuggestedResponseStatus.APPROVED
    )
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_reject_suggested_response(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryTicketRepository,
        InMemoryResponseSuggestionRepository,
        FakeSession,
    ],
) -> None:
    client, repository, suggestion_repository, session = api_client
    ticket = create_ticket(repository)
    suggestion = SuggestedResponse.create(ticket_id=ticket.id, content="Draft reply")
    await suggestion_repository.add(suggestion)

    response = await client.patch(
        f"/api/tickets/{ticket.id}/suggested-responses/{suggestion.id}/reject"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert (
        suggestion_repository.suggestions[suggestion.id].status == SuggestedResponseStatus.REJECTED
    )
    assert session.commit_count == 1
