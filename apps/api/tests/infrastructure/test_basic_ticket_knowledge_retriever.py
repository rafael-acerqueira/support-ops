from uuid import UUID

import pytest

from supportops_api.application.documents import GeneratedEmbedding
from supportops_api.application.response_suggestions import (
    KnowledgeChunkCandidate,
    RetrievedKnowledgeSource,
)
from supportops_api.domain.documents import ProductArea
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.suggestions import BasicTicketKnowledgeRetriever


class InMemoryKnowledgeSourceRepository:
    def __init__(
        self,
        candidates: list[KnowledgeChunkCandidate],
        sources: list[RetrievedKnowledgeSource] | None = None,
    ) -> None:
        self.candidates = candidates
        self.sources = sources or []
        self.limit: int | None = None
        self.search_embedding: tuple[float, ...] | None = None
        self.search_limit: int | None = None

    async def list_indexed_chunks(self, *, limit: int = 50) -> list[KnowledgeChunkCandidate]:
        self.limit = limit
        return self.candidates

    async def search_similar_chunks(
        self,
        *,
        embedding: tuple[float, ...],
        limit: int = 3,
    ) -> list[RetrievedKnowledgeSource]:
        self.search_embedding = embedding
        self.search_limit = limit
        return self.sources


class FakeEmbeddingGenerator:
    def __init__(self) -> None:
        self.text: str | None = None

    async def generate(self, text: str) -> GeneratedEmbedding:
        self.text = text
        return GeneratedEmbedding(values=(0.1, 0.2, 0.3), model="fake")


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


@pytest.mark.asyncio
async def test_basic_ticket_knowledge_retriever_uses_vector_search_when_generator_is_provided() -> (
    None
):
    expected_source = RetrievedKnowledgeSource(
        document_id=UUID("ef9d4205-6c22-481c-b8a7-f4b6d7a7aca6"),
        document_name="refund-policy.md",
        document_type="internal_policy",
        chunk_id=UUID("fb27fd5f-3813-4977-97b5-e129439f7f6c"),
        chunk_index=0,
        content="Validate duplicate invoice charges before promising a refund.",
        relevance_score=0.91,
    )
    repository = InMemoryKnowledgeSourceRepository(candidates=[], sources=[expected_source])
    embedding_generator = FakeEmbeddingGenerator()

    sources = await BasicTicketKnowledgeRetriever(
        repository,
        embedding_generator,
    ).retrieve(create_ticket(), limit=1)

    assert sources == [expected_source]
    assert repository.search_embedding == (0.1, 0.2, 0.3)
    assert repository.search_limit == 50
    assert repository.limit is None
    assert embedding_generator.text is not None
    assert "Duplicate invoice refund request" in embedding_generator.text


@pytest.mark.asyncio
async def test_basic_ticket_knowledge_retriever_filters_low_relevance_vector_sources() -> None:
    relevant_source = RetrievedKnowledgeSource(
        document_id=UUID("ef9d4205-6c22-481c-b8a7-f4b6d7a7aca6"),
        document_name="refund-policy.md",
        document_type="internal_policy",
        chunk_id=UUID("fb27fd5f-3813-4977-97b5-e129439f7f6c"),
        chunk_index=0,
        content="Validate duplicate invoice charges before promising a refund.",
        relevance_score=0.82,
    )
    weak_source = RetrievedKnowledgeSource(
        document_id=UUID("53585070-2a9b-4a59-b78e-e97daef49f1a"),
        document_name="enterprise-sla.md",
        document_type="sla_policy",
        chunk_id=UUID("68d366c3-ce83-42d0-887b-de85eb55747c"),
        chunk_index=0,
        content="Enterprise customers receive a four hour response SLA.",
        relevance_score=0.48,
    )
    repository = InMemoryKnowledgeSourceRepository(
        candidates=[],
        sources=[relevant_source, weak_source],
    )

    sources = await BasicTicketKnowledgeRetriever(
        repository,
        FakeEmbeddingGenerator(),
        min_relevance_score=0.7,
    ).retrieve(create_ticket(), limit=3)

    assert sources == [relevant_source]


@pytest.mark.asyncio
async def test_basic_ticket_knowledge_retriever_filters_low_relevance_keyword_sources() -> None:
    repository = InMemoryKnowledgeSourceRepository(
        [
            create_candidate(
                document_id="53585070-2a9b-4a59-b78e-e97daef49f1a",
                document_name="enterprise-sla.md",
                product_area="support",
                content="Enterprise customers receive a four hour response SLA.",
            )
        ]
    )

    sources = await BasicTicketKnowledgeRetriever(
        repository,
        min_relevance_score=0.7,
    ).retrieve(create_ticket(), limit=3)

    assert sources == []


def test_basic_ticket_knowledge_retriever_rejects_invalid_threshold() -> None:
    repository = InMemoryKnowledgeSourceRepository([])

    with pytest.raises(ValueError, match="min_relevance_score"):
        BasicTicketKnowledgeRetriever(repository, min_relevance_score=1.1)
