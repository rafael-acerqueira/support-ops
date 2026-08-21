import pytest

from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.suggestions import BasicResponseSuggestionGenerator


def create_ticket() -> Ticket:
    return Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Billing export failed",
        description="Customer cannot export invoices.",
        product_area=ProductArea.BILLING,
    )


@pytest.mark.asyncio
async def test_basic_response_suggestion_generator_returns_draft_content() -> None:
    generated_response = await BasicResponseSuggestionGenerator().generate(create_ticket())

    assert "Hi Acme Corp" in generated_response.content
    assert "billing export failed" in generated_response.content
    assert "Next steps:" in generated_response.content
    assert "SupportOps" in generated_response.content
    assert generated_response.sources[0]["document_name"] == "billing-playbook.md"
    assert generated_response.sources[0]["relevance_score"] == 0.82
