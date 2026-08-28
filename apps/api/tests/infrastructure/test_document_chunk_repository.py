from uuid import UUID

from supportops_api.infrastructure.persistence.document_chunk_repository import (
    _distance_to_relevance,
    _record_to_source,
    _vector_distance_expression,
)
from supportops_api.infrastructure.persistence.models import DocumentChunkRecord, DocumentRecord


def test_record_to_source_maps_similarity_result() -> None:
    document = DocumentRecord(
        id=UUID("53585070-2a9b-4a59-b78e-e97daef49f1a"),
        name="refund-policy.md",
        document_type="internal_policy",
        product_area="billing",
        version="v1",
        status="indexed",
        is_active=True,
        tags=["refund"],
        source_file_name="refund-policy.md",
        storage_key="documents/refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        chunk_count=1,
    )
    chunk = DocumentChunkRecord(
        id=UUID("fb27fd5f-3813-4977-97b5-e129439f7f6c"),
        document_id=document.id,
        chunk_index=2,
        content="Validate duplicate invoice charges before promising a refund.",
        chunk_metadata={"section": "Refund policy"},
    )

    source = _record_to_source(document, chunk, distance=0.14)

    assert source.document_id == document.id
    assert source.document_name == "refund-policy.md"
    assert source.document_type == "internal_policy"
    assert source.chunk_id == chunk.id
    assert source.chunk_index == 2
    assert source.content == "Validate duplicate invoice charges before promising a refund."
    assert source.relevance_score == 0.86


def test_distance_to_relevance_clamps_score() -> None:
    assert _distance_to_relevance(0) == 0.99
    assert _distance_to_relevance(0.25) == 0.75
    assert _distance_to_relevance(1.4) == 0.0


def test_vector_distance_expression_returns_float() -> None:
    expression = _vector_distance_expression((0.1, 0.2, 0.3))

    assert expression.type.python_type is float
