from supportops_api.api.schemas import DocumentResponse
from supportops_api.domain.documents import (
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)


def create_document() -> Document:
    return Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy-v1.md",
        content_type="text/markdown",
        size_bytes=1024,
        storage_key="documents/refund-policy/v1.md",
    )


def test_document_response_uses_document_processing_fields_by_default() -> None:
    document = create_document()
    document.start_processing()
    document.mark_indexed(chunk_count=2)

    response = DocumentResponse.from_domain(document)

    assert response.version == "v1"
    assert response.status == DocumentStatus.INDEXED
    assert response.source_file_name == "refund-policy-v1.md"
    assert response.storage_key == "documents/refund-policy/v1.md"
    assert response.chunk_count == 2
    assert response.failure_reason is None
    assert response.last_processed_at == document.last_processed_at


def test_document_response_can_use_document_version_processing_fields() -> None:
    document = create_document()
    version = DocumentVersion.create(
        document_id=document.id,
        version="v2",
        source_file_name="refund-policy-v2.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key="documents/refund-policy/v2.md",
    )
    version.start_processing()
    version.mark_indexed(chunk_count=5)

    response = DocumentResponse.from_domain(document, processing_version=version)

    assert response.id == document.id
    assert response.name == document.name
    assert response.document_type == document.document_type
    assert response.product_area == document.product_area
    assert response.version == "v2"
    assert response.status == DocumentStatus.INDEXED
    assert response.source_file_name == "refund-policy-v2.md"
    assert response.storage_key == "documents/refund-policy/v2.md"
    assert response.size_bytes == 2048
    assert response.chunk_count == 5
    assert response.failure_reason is None
    assert response.last_processed_at == version.last_processed_at
