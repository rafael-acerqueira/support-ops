from uuid import UUID

import pytest

from supportops_api.application.response_suggestions import KnowledgeChunkCandidate
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.suggestions import BasicTicketKnowledgeRetriever


class InMemoryKnowledgeSourceRepository:
    def __init__(self, candidates: list[KnowledgeChunkCandidate]) -> None:
        self.candidates = candidates
        self.limit: int | None = None

    async def list_indexed_chunks(self, *, limit: int = 50) -> list[KnowledgeChunkCandidate]:
        self.limit = limit
        return self.candidates


def create_ticket() -> Ticket:
    return Ticket.create(
        external_id="TCK-1001",
        customer_name="Acme Corp",
        customer_tier="enterprise",
        subject="Duplicate invoice refund request",
        description="Customer reports a duplicate invoice charge and asks for refund guidance.",
        product_area=ProductArea.BILLING,
    )


def create_candidate(
    *,
    document_id: str,
    document_name: str,
    product_area: str,
    content: str,
    tags: tuple[str, ...] = (),
) -> KnowledgeChunkCandidate:
    return KnowledgeChunkCandidate(
        document_id=UUID(document_id),
        document_name=document_name,
        document_type="internal_policy",
        product_area=product_area,
        tags=tags,
        chunk_id=UUID("fb27fd5f-3813-4977-97b5-e129439f7f6c"),
        chunk_index=0,
        content=content,
    )


@pytest.mark.asyncio
async def test_basic_ticket_knowledge_retriever_ranks_candidates() -> None:
    repository = InMemoryKnowledgeSourceRepository(
        [
            create_candidate(
                document_id="53585070-2a9b-4a59-b78e-e97daef49f1a",
                document_name="security-policy.md",
                product_area="security",
                content="Unauthorized account access must be escalated.",
            ),
            create_candidate(
                document_id="ef9d4205-6c22-481c-b8a7-f4b6d7a7aca6",
                document_name="refund-policy.md",
                product_area="billing",
                tags=("refund", "invoice", "enterprise"),
                content="Validate duplicate invoice charges before promising a refund.",
            ),
        ]
    )

    sources = await BasicTicketKnowledgeRetriever(repository).retrieve(create_ticket(), limit=1)

    assert repository.limit == 50
    assert len(sources) == 1
    assert sources[0].document_name == "refund-policy.md"
    assert sources[0].relevance_score > 0
