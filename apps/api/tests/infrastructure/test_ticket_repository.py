import os

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus
from supportops_api.infrastructure.database import get_database_url
from supportops_api.infrastructure.persistence.models import TicketRecord
from supportops_api.infrastructure.persistence.ticket_repository import (
    PostgresTicketRepository,
    _record_to_ticket,
    _ticket_to_record,
)


def create_ticket() -> Ticket:
    ticket = Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Billing export failed",
        description="Customer cannot export invoices.",
        product_area=ProductArea.BILLING,
        priority=TicketPriority.HIGH,
    )
    ticket.mark_triaged()
    return ticket


def test_ticket_record_roundtrip_preserves_domain_values() -> None:
    ticket = create_ticket()

    record = _ticket_to_record(ticket)
    mapped_ticket = _record_to_ticket(record)

    assert mapped_ticket.id == ticket.id
    assert mapped_ticket.external_id == "TCK-1001"
    assert mapped_ticket.customer_name == "Acme Corp"
    assert mapped_ticket.customer_tier == "enterprise"
    assert mapped_ticket.subject == "Billing export failed"
    assert mapped_ticket.description == "Customer cannot export invoices."
    assert mapped_ticket.product_area == ProductArea.BILLING
    assert mapped_ticket.status == TicketStatus.TRIAGED
    assert mapped_ticket.priority == TicketPriority.HIGH
    assert mapped_ticket.created_at == ticket.created_at
    assert mapped_ticket.updated_at == ticket.updated_at


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SUPPORTOPS_RUN_DB_TESTS") != "1",
    reason="Set SUPPORTOPS_RUN_DB_TESTS=1 to run Postgres integration tests.",
)
async def test_postgres_ticket_repository_persists_ticket_workflow() -> None:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ticket = create_ticket()

    try:
        async with session_factory() as session:
            repository = PostgresTicketRepository(session)
            await repository.add(ticket)
            await session.commit()

        async with session_factory() as session:
            repository = PostgresTicketRepository(session)
            stored = await repository.get(ticket.id)

            assert stored is not None
            assert stored.id == ticket.id
            assert stored.external_id == ticket.external_id
            assert stored.status == TicketStatus.TRIAGED
            assert stored.priority == TicketPriority.HIGH

            stored.resolve()
            stored.change_priority(TicketPriority.URGENT)
            await repository.save(stored)
            await session.commit()

        async with session_factory() as session:
            repository = PostgresTicketRepository(session)
            tickets = await repository.list_all()
            stored = await repository.get(ticket.id)

            assert ticket.id in {item.id for item in tickets}
            assert stored is not None
            assert stored.status == TicketStatus.RESOLVED
            assert stored.priority == TicketPriority.URGENT
    finally:
        async with session_factory() as session:
            await session.execute(delete(TicketRecord).where(TicketRecord.id == ticket.id))
            await session.commit()
        await engine.dispose()
