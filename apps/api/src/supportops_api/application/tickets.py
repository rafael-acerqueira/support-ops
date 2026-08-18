from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus


class TicketNotFoundError(Exception):
    def __init__(self, ticket_id: UUID) -> None:
        super().__init__(f"Ticket not found: {ticket_id}")
        self.ticket_id = ticket_id


class TicketRepository(Protocol):
    async def add(self, ticket: Ticket) -> None:
        pass

    async def save(self, ticket: Ticket) -> None:
        pass

    async def get(self, ticket_id: UUID) -> Ticket | None:
        pass

    async def list_all(self) -> list[Ticket]:
        pass


@dataclass(frozen=True)
class CreateTicketInput:
    external_id: str
    customer_name: str
    customer_tier: str
    subject: str
    description: str
    product_area: ProductArea
    priority: TicketPriority = TicketPriority.NORMAL


class CreateTicket:
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, data: CreateTicketInput) -> Ticket:
        ticket = Ticket.create(
            external_id=data.external_id,
            customer_name=data.customer_name,
            customer_tier=data.customer_tier,
            subject=data.subject,
            description=data.description,
            product_area=data.product_area,
            priority=data.priority,
        )

        await self._repository.add(ticket)
        return ticket


class ListTickets:
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Ticket]:
        return await self._repository.list_all()


class GetTicket:
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, ticket_id: UUID) -> Ticket:
        ticket = await self._repository.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)

        return ticket


class ChangeTicketPriority:
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, ticket_id: UUID, priority: TicketPriority) -> Ticket:
        ticket = await self._repository.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)

        ticket.change_priority(priority)
        await self._repository.save(ticket)
        return ticket


class ChangeTicketStatus:
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, ticket_id: UUID, status: TicketStatus) -> Ticket:
        ticket = await self._repository.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)

        match status:
            case TicketStatus.OPEN:
                ticket.reopen()
            case TicketStatus.TRIAGED:
                ticket.mark_triaged()
            case TicketStatus.WAITING_ON_CUSTOMER:
                ticket.wait_on_customer()
            case TicketStatus.WAITING_ON_SUPPORT:
                ticket.wait_on_support()
            case TicketStatus.RESOLVED:
                ticket.resolve()
            case TicketStatus.CLOSED:
                ticket.close()

        await self._repository.save(ticket)
        return ticket
