from uuid import UUID, uuid4

import pytest

from supportops_api.application.tickets import (
    ChangeTicketPriority,
    ChangeTicketStatus,
    CreateTicket,
    CreateTicketInput,
    GetTicket,
    ListTickets,
    TicketNotFoundError,
)
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self.tickets: dict[UUID, Ticket] = {}
        self.saved_tickets: list[Ticket] = []

    async def add(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket

    async def save(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket
        self.saved_tickets.append(ticket)

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return self.tickets.get(ticket_id)

    async def list_all(self) -> list[Ticket]:
        return list(self.tickets.values())


def create_open_ticket() -> Ticket:
    return Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Billing export failed",
        description="Customer cannot export invoices.",
        product_area=ProductArea.BILLING,
    )


@pytest.mark.asyncio
async def test_create_ticket_persists_open_ticket() -> None:
    repository = InMemoryTicketRepository()
    use_case = CreateTicket(repository)

    ticket = await use_case.execute(
        CreateTicketInput(
            external_id=" TCK-1001 ",
            customer_name=" Acme Corp ",
            customer_tier=" Enterprise ",
            subject=" Billing export failed ",
            description=" Customer cannot export invoices. ",
            product_area=ProductArea.BILLING,
            priority=TicketPriority.HIGH,
        )
    )

    assert repository.tickets[ticket.id] == ticket
    assert ticket.external_id == "TCK-1001"
    assert ticket.customer_tier == "enterprise"
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.HIGH


@pytest.mark.asyncio
async def test_list_tickets_returns_all_tickets() -> None:
    repository = InMemoryTicketRepository()
    ticket = create_open_ticket()
    await repository.add(ticket)

    tickets = await ListTickets(repository).execute()

    assert tickets == [ticket]


@pytest.mark.asyncio
async def test_get_ticket_raises_when_ticket_does_not_exist() -> None:
    repository = InMemoryTicketRepository()
    ticket_id = uuid4()

    with pytest.raises(TicketNotFoundError) as error:
        await GetTicket(repository).execute(ticket_id)

    assert error.value.ticket_id == ticket_id


@pytest.mark.asyncio
async def test_change_ticket_priority_saves_ticket() -> None:
    repository = InMemoryTicketRepository()
    ticket = create_open_ticket()
    await repository.add(ticket)

    updated = await ChangeTicketPriority(repository).execute(ticket.id, TicketPriority.URGENT)

    assert updated.priority == TicketPriority.URGENT
    assert repository.saved_tickets == [ticket]


@pytest.mark.asyncio
async def test_change_ticket_status_saves_ticket() -> None:
    repository = InMemoryTicketRepository()
    ticket = create_open_ticket()
    await repository.add(ticket)

    updated = await ChangeTicketStatus(repository).execute(ticket.id, TicketStatus.TRIAGED)

    assert updated.status == TicketStatus.TRIAGED
    assert repository.saved_tickets == [ticket]
