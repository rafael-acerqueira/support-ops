from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from supportops_api.domain.documents import ProductArea


class TicketStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_SUPPORT = "waiting_on_support"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Ticket:
    external_id: str
    customer_name: str
    customer_tier: str
    subject: str
    description: str
    product_area: ProductArea
    id: UUID = field(default_factory=uuid4)
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.NORMAL
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.external_id = self.external_id.strip()
        self.customer_name = self.customer_name.strip()
        self.customer_tier = self.customer_tier.strip().lower()
        self.subject = self.subject.strip()
        self.description = self.description.strip()

        if not self.external_id:
            raise ValueError("Ticket external id is required")
        if not self.customer_name:
            raise ValueError("Customer name is required")
        if not self.customer_tier:
            raise ValueError("Customer tier is required")
        if not self.subject:
            raise ValueError("Ticket subject is required")
        if not self.description:
            raise ValueError("Ticket description is required")

    @classmethod
    def create(
        cls,
        *,
        external_id: str,
        customer_name: str,
        customer_tier: str,
        subject: str,
        description: str,
        product_area: ProductArea,
        priority: TicketPriority = TicketPriority.NORMAL,
    ) -> Ticket:
        return cls(
            external_id=external_id,
            customer_name=customer_name,
            customer_tier=customer_tier,
            subject=subject,
            description=description,
            product_area=product_area,
            priority=priority,
        )

    def mark_triaged(self) -> None:
        self.status = TicketStatus.TRIAGED
        self.updated_at = _utcnow()

    def wait_on_customer(self) -> None:
        self.status = TicketStatus.WAITING_ON_CUSTOMER
        self.updated_at = _utcnow()

    def wait_on_support(self) -> None:
        self.status = TicketStatus.WAITING_ON_SUPPORT
        self.updated_at = _utcnow()

    def resolve(self) -> None:
        self.status = TicketStatus.RESOLVED
        self.updated_at = _utcnow()

    def close(self) -> None:
        self.status = TicketStatus.CLOSED
        self.updated_at = _utcnow()

    def reopen(self) -> None:
        self.status = TicketStatus.OPEN
        self.updated_at = _utcnow()

    def change_priority(self, priority: TicketPriority) -> None:
        self.priority = priority
        self.updated_at = _utcnow()
