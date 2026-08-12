from io import BytesIO
from uuid import uuid4

import pytest

from supportops_api.application.documents import StoredDocumentFile
from supportops_api.domain.documents import Document, DocumentType, ProductArea
from supportops_api.infrastructure.processing import BasicDocumentProcessor


class InMemoryDocumentStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def save(self, *, file_name: str, content_type: str, content) -> StoredDocumentFile:
        data = content.read()
        storage_key = f"fake/{file_name}"
        self.files[storage_key] = data
        return StoredDocumentFile(
            storage_key=storage_key,
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(data),
        )

    async def open(self, storage_key: str):
        return BytesIO(self.files[storage_key])


def create_document(*, storage_key: str | None = "fake/refund-policy.md") -> Document:
    return Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        storage_key=storage_key,
    )


@pytest.mark.asyncio
async def test_basic_document_processor_creates_chunks_from_text() -> None:
    storage = InMemoryDocumentStorage()
    stored_file = await storage.save(
        file_name="refund-policy.md",
        content_type="text/markdown",
        content=BytesIO(b"First paragraph.\n\nSecond paragraph."),
    )
    document = create_document(storage_key=stored_file.storage_key)

    chunks = await BasicDocumentProcessor(storage, max_chunk_chars=20).process(document)

    assert [chunk.content for chunk in chunks] == ["First paragraph.", "Second paragraph."]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert chunks[0].document_id == document.id
    assert chunks[0].metadata == {"source_file_name": "refund-policy.md"}


@pytest.mark.asyncio
async def test_basic_document_processor_requires_storage_key() -> None:
    storage = InMemoryDocumentStorage()
    document = create_document(storage_key=None)

    with pytest.raises(ValueError, match="no storage key"):
        await BasicDocumentProcessor(storage).process(document)


@pytest.mark.asyncio
async def test_basic_document_processor_rejects_unsupported_content_type() -> None:
    storage = InMemoryDocumentStorage()
    document = create_document()
    document.content_type = "application/pdf"

    with pytest.raises(ValueError, match="Unsupported content type"):
        await BasicDocumentProcessor(storage).process(document)


@pytest.mark.asyncio
async def test_basic_document_processor_rejects_empty_content() -> None:
    storage = InMemoryDocumentStorage()
    stored_file = await storage.save(
        file_name="empty.md",
        content_type="text/markdown",
        content=BytesIO(b"   "),
    )
    document = create_document(storage_key=stored_file.storage_key)

    with pytest.raises(ValueError, match="content is empty"):
        await BasicDocumentProcessor(storage).process(document)


def test_basic_document_processor_requires_positive_chunk_size() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        BasicDocumentProcessor(InMemoryDocumentStorage(), max_chunk_chars=0)
