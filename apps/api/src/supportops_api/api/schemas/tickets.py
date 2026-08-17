from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus


class CreateTicketRequest(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_tier: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    product_area: ProductArea
    priority: TicketPriority = TicketPriority.NORMAL


class UpdateTicketPriorityRequest(BaseModel):
    priority: TicketPriority


class UpdateTicketStatusRequest(BaseModel):
    status: TicketStatus


class TicketResponse(BaseModel):
    id: UUID
    external_id: str
    customer_name: str
    customer_tier: str
    subject: str
    description: str
    product_area: ProductArea
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, ticket: Ticket) -> TicketResponse:
        return cls(
            id=ticket.id,
            external_id=ticket.external_id,
            customer_name=ticket.customer_name,
            customer_tier=ticket.customer_tier,
            subject=ticket.subject,
            description=ticket.description,
            product_area=ticket.product_area,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
