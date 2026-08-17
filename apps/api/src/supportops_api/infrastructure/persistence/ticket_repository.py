from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.tickets import TicketRepository
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus
from supportops_api.infrastructure.persistence.models import TicketRecord


class PostgresTicketRepository(TicketRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, ticket: Ticket) -> None:
        self._session.add(_ticket_to_record(ticket))
        await self._session.flush()

    async def save(self, ticket: Ticket) -> None:
        record = await self._session.get(TicketRecord, ticket.id)
        if record is None:
            self._session.add(_ticket_to_record(ticket))
        else:
            _update_ticket_record(record, ticket)

        await self._session.flush()

    async def get(self, ticket_id: UUID) -> Ticket | None:
        record = await self._session.get(TicketRecord, ticket_id)
        if record is None:
            return None

        return _record_to_ticket(record)

    async def list_all(self) -> list[Ticket]:
        result = await self._session.execute(
            select(TicketRecord).order_by(TicketRecord.created_at.desc())
        )
        return [_record_to_ticket(record) for record in result.scalars()]


def _ticket_to_record(ticket: Ticket) -> TicketRecord:
    return TicketRecord(
        id=ticket.id,
        external_id=ticket.external_id,
        customer_name=ticket.customer_name,
        customer_tier=ticket.customer_tier,
        subject=ticket.subject,
        description=ticket.description,
        product_area=ticket.product_area.value,
        status=ticket.status.value,
        priority=ticket.priority.value,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _update_ticket_record(record: TicketRecord, ticket: Ticket) -> None:
    record.external_id = ticket.external_id
    record.customer_name = ticket.customer_name
    record.customer_tier = ticket.customer_tier
    record.subject = ticket.subject
    record.description = ticket.description
    record.product_area = ticket.product_area.value
    record.status = ticket.status.value
    record.priority = ticket.priority.value
    record.created_at = ticket.created_at
    record.updated_at = ticket.updated_at


def _record_to_ticket(record: TicketRecord) -> Ticket:
    return Ticket(
        id=record.id,
        external_id=record.external_id,
        customer_name=record.customer_name,
        customer_tier=record.customer_tier,
        subject=record.subject,
        description=record.description,
        product_area=ProductArea(record.product_area),
        status=TicketStatus(record.status),
        priority=TicketPriority(record.priority),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
