from uuid import uuid4

import pytest

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    ProductArea,
)


def test_document_starts_uploaded_and_normalizes_tags() -> None:
    document = Document.create(
        name=" Refund Policy ",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name=" refund-policy.md ",
        content_type=" text/markdown ",
        size_bytes=1024,
        tags=(" Enterprise ", "refund", "", "REFUND"),
        storage_key=" documents/refund-policy.md ",
    )

    assert document.name == "Refund Policy"
    assert document.status == DocumentStatus.UPLOADED
    assert document.version == "v1"
    assert document.is_active is True
    assert document.tags == ("enterprise", "refund")
    assert document.storage_key == "documents/refund-policy.md"


def test_document_moves_through_processing_and_indexed_states() -> None:
    document = Document.create(
        name="Enterprise SLA",
        document_type=DocumentType.SLA_POLICY,
        product_area=ProductArea.SUPPORT,
        source_file_name="enterprise-sla.md",
        content_type="text/markdown",
        size_bytes=2048,
    )

    document.start_processing()
    document.mark_indexed(chunk_count=7)

    assert document.status == DocumentStatus.INDEXED
    assert document.chunk_count == 7
    assert document.failure_reason is None
    assert document.last_processed_at is not None


def test_document_requires_chunks_to_be_marked_indexed() -> None:
    document = Document.create(
        name="Security Policy",
        document_type=DocumentType.SECURITY_POLICY,
        product_area=ProductArea.SECURITY,
        source_file_name="security-policy.md",
        content_type="text/markdown",
        size_bytes=4096,
    )

    with pytest.raises(ValueError, match="at least one chunk"):
        document.mark_indexed(chunk_count=0)


def test_document_can_be_deactivated_and_reactivated_without_changing_processing_status() -> None:
    document = Document.create(
        name="Incident Policy",
        document_type=DocumentType.INCIDENT_POLICY,
        product_area=ProductArea.SUPPORT,
        source_file_name="incident-policy.md",
        content_type="text/markdown",
        size_bytes=512,
    )
    document.start_processing()
    document.mark_indexed(chunk_count=3)

    document.deactivate()
    assert document.is_active is False
    assert document.status == DocumentStatus.INDEXED

    document.activate()
    assert document.is_active is True
    assert document.status == DocumentStatus.INDEXED


def test_document_records_failure_reason() -> None:
    document = Document.create(
        name="Billing Playbook",
        document_type=DocumentType.PLAYBOOK,
        product_area=ProductArea.BILLING,
        source_file_name="billing-playbook.pdf",
        content_type="application/pdf",
        size_bytes=8192,
    )

    document.mark_failed("Unsupported file content")

    assert document.status == DocumentStatus.FAILED
    assert document.failure_reason == "Unsupported file content"


def test_document_chunk_requires_non_empty_content() -> None:
    with pytest.raises(ValueError, match="content is required"):
        DocumentChunk(document_id=uuid4(), chunk_index=0, content="   ")


def test_document_chunk_trims_content() -> None:
    chunk = DocumentChunk(document_id=uuid4(), chunk_index=1, content="  SLA response window  ")

    assert chunk.content == "SLA response window"


def test_document_chunk_preserves_embedding_values() -> None:
    chunk = DocumentChunk(
        document_id=uuid4(),
        chunk_index=1,
        content="SLA response window",
        embedding=(0.1, -0.2),
        embedding_provider=" OpenAI ",
        embedding_model=" text-embedding-3-small ",
    )

    assert chunk.embedding == (0.1, -0.2)
    assert chunk.embedding_provider == "openai"
    assert chunk.embedding_model == "text-embedding-3-small"


def test_document_chunk_rejects_empty_embedding() -> None:
    with pytest.raises(ValueError, match="embedding cannot be empty"):
        DocumentChunk(
            document_id=uuid4(),
            chunk_index=1,
            content="SLA response window",
            embedding=(),
        )


def test_document_chunk_rejects_empty_embedding_provider() -> None:
    with pytest.raises(ValueError, match="embedding provider"):
        DocumentChunk(
            document_id=uuid4(),
            chunk_index=1,
            content="SLA response window",
            embedding_provider="   ",
        )


def test_document_chunk_rejects_empty_embedding_model() -> None:
    with pytest.raises(ValueError, match="embedding model"):
        DocumentChunk(
            document_id=uuid4(),
            chunk_index=1,
            content="SLA response window",
            embedding_model="   ",
        )
