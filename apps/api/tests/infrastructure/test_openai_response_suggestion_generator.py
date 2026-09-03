from types import SimpleNamespace
from uuid import UUID

from openai import APIConnectionError
import pytest

from supportops_api.application.response_suggestions import (
    ResponseGenerationProviderError,
    RetrievedKnowledgeSource,
)
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.suggestions import OpenAIResponseSuggestionGenerator


class FakeResponsesClient:
    def __init__(self, output_text: str = "Hi Acme, here is a suggested response.") -> None:
        self.output_text = output_text
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponsesClient | None = None) -> None:
        self.responses = responses or FakeResponsesClient()


class FailingResponsesClient:
    async def create(self, **kwargs: object) -> SimpleNamespace:
        raise APIConnectionError(request=None)


class FailingOpenAIClient:
    responses = FailingResponsesClient()


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
async def test_openai_response_suggestion_generator_returns_suggestion() -> None:
    responses = FakeResponsesClient("Hi Acme Corp,\n\nWe can help with this billing issue.")
    client = FakeOpenAIClient(responses)
    generator = OpenAIResponseSuggestionGenerator(
        FakeKnowledgeRetriever(),
        model="gpt-4o-mini",
        client=client,
    )

    generated = await generator.generate(create_ticket())

    assert generated.content == "Hi Acme Corp,\n\nWe can help with this billing issue."
    assert generated.sources == [
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
    assert responses.requests[0]["model"] == "gpt-4o-mini"
    instructions = str(responses.requests[0]["instructions"])
    input_text = str(responses.requests[0]["input"])
    assert "# Hard constraints" in instructions
    assert "Do not invent policies" in instructions
    assert "Internal review note" in instructions
    assert "# Ticket" in input_text
    assert "Billing export failed" in input_text
    assert "# Retrieved internal knowledge sources" in input_text
    assert "Validate duplicate invoice charges" in input_text
    assert "# Task" in input_text


@pytest.mark.asyncio
async def test_openai_response_suggestion_generator_rejects_empty_output() -> None:
    client = FakeOpenAIClient(FakeResponsesClient("   "))
    generator = OpenAIResponseSuggestionGenerator(FakeKnowledgeRetriever(), client=client)

    with pytest.raises(ResponseGenerationProviderError, match="empty content"):
        await generator.generate(create_ticket())


@pytest.mark.asyncio
async def test_openai_response_suggestion_generator_wraps_provider_errors() -> None:
    generator = OpenAIResponseSuggestionGenerator(
        FakeKnowledgeRetriever(),
        client=FailingOpenAIClient(),
    )

    with pytest.raises(ResponseGenerationProviderError, match="connection failed"):
        await generator.generate(create_ticket())
