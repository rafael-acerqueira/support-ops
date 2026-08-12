from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentType,
    ProductArea,
)


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"Document not found: {document_id}")
        self.document_id = document_id


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None:
        pass

    async def save(self, document: Document) -> None:
        pass

    async def get(self, document_id: UUID) -> Document | None:
        pass

    async def list_all(self) -> list[Document]:
        pass

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        pass


class DocumentProcessor(Protocol):
    async def process(self, document: Document) -> list[DocumentChunk]:
        pass


@dataclass(frozen=True)
class EnqueuedDocumentProcessing:
    document_id: UUID
    task_id: str


class DocumentProcessingQueue(Protocol):
    async def enqueue(self, document_id: UUID) -> EnqueuedDocumentProcessing:
        pass


@dataclass(frozen=True)
class StoredDocumentFile:
    storage_key: str
    file_name: str
    content_type: str
    size_bytes: int


class DocumentStorage(Protocol):
    async def save(
        self,
        *,
        file_name: str,
        content_type: str,
        content: BinaryIO,
    ) -> StoredDocumentFile:
        pass

    async def open(self, storage_key: str) -> BinaryIO:
        pass


@dataclass(frozen=True)
class CreateDocumentInput:
    name: str
    document_type: DocumentType
    product_area: ProductArea
    source_file_name: str
    content_type: str
    size_bytes: int
    tags: tuple[str, ...] = ()
    storage_key: str | None = None


class CreateDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, data: CreateDocumentInput) -> Document:
        document = Document.create(
            name=data.name,
            document_type=data.document_type,
            product_area=data.product_area,
            source_file_name=data.source_file_name,
            content_type=data.content_type,
            size_bytes=data.size_bytes,
            tags=data.tags,
            storage_key=data.storage_key,
        )

        await self._repository.add(document)
        return document


class ListDocuments:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Document]:
        return await self._repository.list_all()


class GetDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        return document


class ActivateDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        document.activate()
        await self._repository.save(document)
        return document


class DeactivateDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        document.deactivate()
        await self._repository.save(document)
        return document


class ProcessDocument:
    def __init__(self, repository: DocumentRepository, processor: DocumentProcessor) -> None:
        self._repository = repository
        self._processor = processor

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        document.start_processing()
        await self._repository.save(document)

        try:
            chunks = await self._processor.process(document)
            document.mark_indexed(chunk_count=len(chunks))
            await self._repository.replace_chunks(document.id, chunks)
        except Exception as exc:
            document.mark_failed(str(exc))
            raise
        finally:
            await self._repository.save(document)

        return document
