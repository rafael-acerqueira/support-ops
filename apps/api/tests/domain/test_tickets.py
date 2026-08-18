import pytest

from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket, TicketPriority, TicketStatus


def test_ticket_starts_open_and_normalizes_text_fields() -> None:
    ticket = Ticket.create(
        external_id=" TCK-1001 ",
        customer_name=" Acme Corp ",
        customer_tier=" Enterprise ",
        subject=" Billing export failed ",
        description=" Customer cannot export invoices. ",
        product_area=ProductArea.BILLING,
        priority=TicketPriority.HIGH,
    )

    assert ticket.external_id == "TCK-1001"
    assert ticket.customer_name == "Acme Corp"
    assert ticket.customer_tier == "enterprise"
    assert ticket.subject == "Billing export failed"
    assert ticket.description == "Customer cannot export invoices."
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.product_area == ProductArea.BILLING


def test_ticket_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="external id is required"):
        Ticket.create(
            external_id="   ",
            customer_name="Acme Corp",
            customer_tier="enterprise",
            subject="Billing export failed",
            description="Customer cannot export invoices.",
            product_area=ProductArea.BILLING,
        )

    with pytest.raises(ValueError, match="Customer name is required"):
        Ticket.create(
            external_id="TCK-1001",
            customer_name="   ",
            customer_tier="enterprise",
            subject="Billing export failed",
            description="Customer cannot export invoices.",
            product_area=ProductArea.BILLING,
        )

    with pytest.raises(ValueError, match="Ticket subject is required"):
        Ticket.create(
            external_id="TCK-1001",
            customer_name="Acme Corp",
            customer_tier="enterprise",
            subject="   ",
            description="Customer cannot export invoices.",
            product_area=ProductArea.BILLING,
        )


def test_ticket_moves_through_support_statuses() -> None:
    ticket = Ticket.create(
        external_id="TCK-1002",
        customer_name="Globex",
        customer_tier="business",
        subject="API timeout",
        description="Requests to the search endpoint time out.",
        product_area=ProductArea.API,
    )

    ticket.mark_triaged()
    assert ticket.status == TicketStatus.TRIAGED

    ticket.wait_on_customer()
    assert ticket.status == TicketStatus.WAITING_ON_CUSTOMER

    ticket.wait_on_support()
    assert ticket.status == TicketStatus.WAITING_ON_SUPPORT

    ticket.resolve()
    assert ticket.status == TicketStatus.RESOLVED

    ticket.close()
    assert ticket.status == TicketStatus.CLOSED

    ticket.reopen()
    assert ticket.status == TicketStatus.OPEN


def test_ticket_priority_can_change() -> None:
    ticket = Ticket.create(
        external_id="TCK-1003",
        customer_name="Initech",
        customer_tier="startup",
        subject="SAML setup question",
        description="Customer needs help configuring SAML.",
        product_area=ProductArea.SECURITY,
    )

    ticket.change_priority(TicketPriority.URGENT)

    assert ticket.priority == TicketPriority.URGENT
