from uuid import UUID

import pytest

from supportops_api.application.response_suggestions import RetrievedKnowledgeSource
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.response_suggestions import SuggestedResponseConfidenceLevel
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
    assert "needs careful human review" in generated_response.content
    assert "SupportOps" in generated_response.content
    assert generated_response.sources == []
    assert generated_response.confidence_score is None
    assert generated_response.confidence_level == SuggestedResponseConfidenceLevel.LOW
    assert (
        generated_response.confidence_reason
        == "No trusted knowledge sources were retrieved for this ticket."
    )


@pytest.mark.asyncio
async def test_basic_response_suggestion_generator_uses_retrieved_sources() -> None:
    generated_response = await BasicResponseSuggestionGenerator(FakeKnowledgeRetriever()).generate(
        create_ticket()
    )

    assert "I reviewed the indexed internal sources" in generated_response.content
    assert generated_response.sources == [
        {
            "document_id": "53585070-2a9b-4a59-b78e-e97daef49f1a",
            "chunk_id": "fb27fd5f-3813-4977-97b5-e129439f7f6c",
            "chunk_index": 0,
            "document_name": "billing-playbook.md",
            "document_type": "playbook",
            "relevance_score": 0.91,
            "excerpt": "Validate duplicate invoice charges before promising a refund.",
        }
    ]
    assert generated_response.confidence_score == 0.91
    assert generated_response.confidence_level == SuggestedResponseConfidenceLevel.HIGH
    assert (
        generated_response.confidence_reason
        == "Best retrieved source matched this ticket with 91% relevance from billing-playbook.md."
    )


class FakeKnowledgeRetriever:
    async def retrieve(self, ticket: Ticket, *, limit: int = 3) -> list[RetrievedKnowledgeSource]:
        return [
            RetrievedKnowledgeSource(
                document_id=UUID("53585070-2a9b-4a59-b78e-e97daef49f1a"),
                document_name="billing-playbook.md",
                document_type="playbook",
                chunk_id=UUID("fb27fd5f-3813-4977-97b5-e129439f7f6c"),
                chunk_index=0,
                content="Validate duplicate invoice charges before promising a refund.",
                relevance_score=0.91,
            )
        ]
