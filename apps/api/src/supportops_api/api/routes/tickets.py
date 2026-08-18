from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.api.dependencies import (
    get_response_suggestion_generator,
    get_response_suggestion_repository,
    get_ticket_repository,
)
from supportops_api.api.schemas import (
    CreateTicketRequest,
    SuggestedResponseResponse,
    TicketResponse,
    UpdateTicketPriorityRequest,
    UpdateTicketStatusRequest,
)
from supportops_api.application.response_suggestions import (
    ApproveSuggestedResponse,
    GenerateSuggestedResponse,
    GenerateSuggestedResponseInput,
    ListSuggestedResponses,
    RejectSuggestedResponse,
    ResponseSuggestionGenerator,
    ResponseSuggestionRepository,
    SuggestedResponseNotFoundError,
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


def _suggestion_not_found_error(error: SuggestedResponseNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "message": "Suggested response not found",
            "suggestion_id": str(error.suggestion_id),
        },
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


@router.post(
    "/{ticket_id}/suggested-responses",
    response_model=SuggestedResponseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_suggested_response(
    ticket_id: UUID,
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    suggestion_repository: ResponseSuggestionRepository = Depends(
        get_response_suggestion_repository
    ),
    generator: ResponseSuggestionGenerator = Depends(get_response_suggestion_generator),
    session: AsyncSession = Depends(get_session),
) -> SuggestedResponseResponse:
    try:
        suggestion = await GenerateSuggestedResponse(
            ticket_repository, suggestion_repository, generator
        ).execute(GenerateSuggestedResponseInput(ticket_id=ticket_id))
    except TicketNotFoundError as error:
        raise _not_found_error(error) from error

    await session.commit()
    return SuggestedResponseResponse.from_domain(suggestion)


@router.get("/{ticket_id}/suggested-responses", response_model=list[SuggestedResponseResponse])
async def list_suggested_responses(
    ticket_id: UUID,
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    suggestion_repository: ResponseSuggestionRepository = Depends(
        get_response_suggestion_repository
    ),
) -> list[SuggestedResponseResponse]:
    try:
        suggestions = await ListSuggestedResponses(
            ticket_repository, suggestion_repository
        ).execute(ticket_id)
    except TicketNotFoundError as error:
        raise _not_found_error(error) from error

    return [SuggestedResponseResponse.from_domain(suggestion) for suggestion in suggestions]


@router.patch(
    "/{ticket_id}/suggested-responses/{suggestion_id}/approve",
    response_model=SuggestedResponseResponse,
)
async def approve_suggested_response(
    ticket_id: UUID,
    suggestion_id: UUID,
    repository: ResponseSuggestionRepository = Depends(get_response_suggestion_repository),
    session: AsyncSession = Depends(get_session),
) -> SuggestedResponseResponse:
    try:
        suggestion = await ApproveSuggestedResponse(repository).execute(ticket_id, suggestion_id)
    except SuggestedResponseNotFoundError as error:
        raise _suggestion_not_found_error(error) from error

    await session.commit()
    return SuggestedResponseResponse.from_domain(suggestion)


@router.patch(
    "/{ticket_id}/suggested-responses/{suggestion_id}/reject",
    response_model=SuggestedResponseResponse,
)
async def reject_suggested_response(
    ticket_id: UUID,
    suggestion_id: UUID,
    repository: ResponseSuggestionRepository = Depends(get_response_suggestion_repository),
    session: AsyncSession = Depends(get_session),
) -> SuggestedResponseResponse:
    try:
        suggestion = await RejectSuggestedResponse(repository).execute(ticket_id, suggestion_id)
    except SuggestedResponseNotFoundError as error:
        raise _suggestion_not_found_error(error) from error

    await session.commit()
    return SuggestedResponseResponse.from_domain(suggestion)
