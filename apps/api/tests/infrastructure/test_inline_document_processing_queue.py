from uuid import UUID

import pytest

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    ProductArea,
)
from supportops_api.infrastructure.queues import InlineDocumentProcessingQueue


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[UUID, Document] = {}
        self.chunks: dict[UUID, list[DocumentChunk]] = {}

    async def add(self, document: Document) -> None:
        self.documents[document.id] = document

    async def save(self, document: Document) -> None:
        self.documents[document.id] = document

    async def get(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    async def list_all(self) -> list[Document]:
        return list(self.documents.values())

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        self.chunks[document_id] = chunks


class FakeDocumentProcessor:
    async def process(self, document: Document) -> list[DocumentChunk]:
        return [DocumentChunk(document_id=document.id, chunk_index=0, content="Processed chunk")]


def create_document() -> Document:
    return Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        storage_key="fake/refund-policy.md",
    )


@pytest.mark.asyncio
async def test_inline_document_processing_queue_processes_document_immediately() -> None:
    repository = InMemoryDocumentRepository()
    document = create_document()
    await repository.add(document)

    processed = await InlineDocumentProcessingQueue(repository, FakeDocumentProcessor()).enqueue(
        document.id
    )

    assert processed.status == DocumentStatus.INDEXED
    assert processed.chunk_count == 1
    assert repository.chunks[document.id][0].content == "Processed chunk"
