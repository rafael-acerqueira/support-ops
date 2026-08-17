from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.api.dependencies import get_ticket_repository
from supportops_api.api.schemas import (
    CreateTicketRequest,
    TicketResponse,
    UpdateTicketPriorityRequest,
    UpdateTicketStatusRequest,
)
from supportops_api.application.tickets import (
    ChangeTicketPriority,
    ChangeTicketStatus,
    CreateTicket,
    CreateTicketInput,
    GetTicket,
    ListTickets,
    TicketNotFoundError,
    TicketRepository,
)
from supportops_api.infrastructure.database import get_session

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _not_found_error(error: TicketNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": "Ticket not found", "ticket_id": str(error.ticket_id)},
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: CreateTicketRequest,
    repository: TicketRepository = Depends(get_ticket_repository),
    session: AsyncSession = Depends(get_session),
) -> TicketResponse:
    ticket = await CreateTicket(repository).execute(
        CreateTicketInput(
            external_id=payload.external_id,
            customer_name=payload.customer_name,
            customer_tier=payload.customer_tier,
            subject=payload.subject,
            description=payload.description,
            product_area=payload.product_area,
            priority=payload.priority,
        )
    )

    await session.commit()
    return TicketResponse.from_domain(ticket)


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    repository: TicketRepository = Depends(get_ticket_repository),
) -> list[TicketResponse]:
    tickets = await ListTickets(repository).execute()
    return [TicketResponse.from_domain(ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    repository: TicketRepository = Depends(get_ticket_repository),
) -> TicketResponse:
    try:
        ticket = await GetTicket(repository).execute(ticket_id)
    except TicketNotFoundError as error:
        raise _not_found_error(error) from error

    return TicketResponse.from_domain(ticket)


@router.patch("/{ticket_id}/priority", response_model=TicketResponse)
async def update_ticket_priority(
    ticket_id: UUID,
    payload: UpdateTicketPriorityRequest,
    repository: TicketRepository = Depends(get_ticket_repository),
    session: AsyncSession = Depends(get_session),
) -> TicketResponse:
    try:
        ticket = await ChangeTicketPriority(repository).execute(ticket_id, payload.priority)
    except TicketNotFoundError as error:
        raise _not_found_error(error) from error

    await session.commit()
    return TicketResponse.from_domain(ticket)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: UUID,
    payload: UpdateTicketStatusRequest,
    repository: TicketRepository = Depends(get_ticket_repository),
    session: AsyncSession = Depends(get_session),
) -> TicketResponse:
    try:
        ticket = await ChangeTicketStatus(repository).execute(ticket_id, payload.status)
    except TicketNotFoundError as error:
        raise _not_found_error(error) from error

    await session.commit()
    return TicketResponse.from_domain(ticket)
