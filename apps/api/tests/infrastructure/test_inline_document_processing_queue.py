from uuid import UUID

import pytest

from supportops_api.application.documents import GeneratedEmbedding
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
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


class InMemoryDocumentVersionRepository:
    def __init__(self) -> None:
        self.versions: dict[UUID, DocumentVersion] = {}

    async def add(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version

    async def save(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        return self.versions.get(version_id)

    async def list_for_document(self, document_id: UUID) -> list[DocumentVersion]:
        return [version for version in self.versions.values() if version.document_id == document_id]

    async def deactivate_all_for_document(self, document_id: UUID) -> None:
        for version in self.versions.values():
            if version.document_id == document_id:
                version.deactivate()


class FakeDocumentProcessor:
    async def process(self, document: Document) -> list[DocumentChunk]:
        return [DocumentChunk(document_id=document.id, chunk_index=0, content="Processed chunk")]


class FakeEmbeddingGenerator:
    async def generate(self, text: str) -> GeneratedEmbedding:
        return GeneratedEmbedding(values=(0.4, 0.8), model="fake")


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

    enqueued = await InlineDocumentProcessingQueue(repository, FakeDocumentProcessor()).enqueue(
        document.id
    )

    assert enqueued.document_id == document.id
    assert enqueued.task_id == f"inline:{document.id}"
    assert repository.documents[document.id].status == DocumentStatus.INDEXED
    assert repository.documents[document.id].chunk_count == 1
    assert repository.chunks[document.id][0].content == "Processed chunk"


@pytest.mark.asyncio
async def test_inline_document_processing_queue_can_generate_embeddings() -> None:
    repository = InMemoryDocumentRepository()
    document = create_document()
    await repository.add(document)

    await InlineDocumentProcessingQueue(
        repository,
        FakeDocumentProcessor(),
        FakeEmbeddingGenerator(),
    ).enqueue(document.id)

    assert repository.chunks[document.id][0].embedding == (0.4, 0.8)


@pytest.mark.asyncio
async def test_inline_document_processing_queue_syncs_current_version() -> None:
    repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_document()
    version = DocumentVersion.create(
        document_id=document.id,
        version=document.version,
        source_file_name=document.source_file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        storage_key=document.storage_key or "",
    )
    await repository.add(document)
    await version_repository.add(version)

    await InlineDocumentProcessingQueue(
        repository,
        FakeDocumentProcessor(),
        version_repository=version_repository,
    ).enqueue(document.id)

    assert version.status == DocumentStatus.INDEXED
    assert version.is_active is True
    assert version.chunk_count == 1
