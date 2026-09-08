from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentType,
    DocumentVersion,
    ProductArea,
)


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"Document not found: {document_id}")
        self.document_id = document_id


class DocumentVersionNotFoundError(Exception):
    def __init__(self, document_version_id: UUID) -> None:
        super().__init__(f"Document version not found: {document_version_id}")
        self.document_version_id = document_version_id


class EmbeddingProviderError(Exception):
    pass


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None:
        pass

    async def save(self, document: Document) -> None:
        pass

    async def get(self, document_id: UUID) -> Document | None:
        pass

    async def list_all(self) -> list[Document]:
        pass

    async def list_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        pass

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        pass


class DocumentVersionRepository(Protocol):
    async def add(self, version: DocumentVersion) -> None:
        pass

    async def save(self, version: DocumentVersion) -> None:
        pass

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        pass

    async def list_for_document(self, document_id: UUID) -> list[DocumentVersion]:
        pass

    async def deactivate_all_for_document(self, document_id: UUID) -> None:
        pass


class DocumentProcessor(Protocol):
    async def process(self, document: Document) -> list[DocumentChunk]:
        pass


@dataclass(frozen=True)
class GeneratedEmbedding:
    values: tuple[float, ...]
    model: str
    provider: str = "unknown"

    @property
    def dimensions(self) -> int:
        return len(self.values)


class EmbeddingGenerator(Protocol):
    async def generate(self, text: str) -> GeneratedEmbedding:
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


@dataclass(frozen=True)
class CreateDocumentVersionInput:
    document_id: UUID
    version: str
    source_file_name: str
    content_type: str
    size_bytes: int
    storage_key: str


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


class CreateDocumentVersion:
    def __init__(
        self,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
    ) -> None:
        self._document_repository = document_repository
        self._version_repository = version_repository

    async def execute(self, data: CreateDocumentVersionInput) -> DocumentVersion:
        document = await self._document_repository.get(data.document_id)
        if document is None:
            raise DocumentNotFoundError(data.document_id)

        version = DocumentVersion.create(
            document_id=document.id,
            version=data.version,
            source_file_name=data.source_file_name,
            content_type=data.content_type,
            size_bytes=data.size_bytes,
            storage_key=data.storage_key,
        )
        await self._version_repository.add(version)
        return version


class ListDocuments:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Document]:
        return await self._repository.list_all()


class ListDocumentVersions:
    def __init__(
        self,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
    ) -> None:
        self._document_repository = document_repository
        self._version_repository = version_repository

    async def execute(self, document_id: UUID) -> list[DocumentVersion]:
        document = await self._document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        return await self._version_repository.list_for_document(document_id)


class GetDocument:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        return document


class ActivateDocumentVersion:
    def __init__(
        self,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
    ) -> None:
        self._document_repository = document_repository
        self._version_repository = version_repository

    async def execute(self, document_id: UUID, version_id: UUID) -> DocumentVersion:
        document = await self._document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        version = await self._version_repository.get(version_id)
        if version is None or version.document_id != document.id:
            raise DocumentVersionNotFoundError(version_id)

        await self._version_repository.deactivate_all_for_document(document.id)
        version.activate()
        _sync_document_from_version(document, version)

        await self._version_repository.save(version)
        await self._document_repository.save(document)
        return version


class ListDocumentChunks:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> list[DocumentChunk]:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        return await self._repository.list_chunks(document_id)


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
    def __init__(
        self,
        repository: DocumentRepository,
        processor: DocumentProcessor,
        embedding_generator: EmbeddingGenerator | None = None,
    ) -> None:
        self._repository = repository
        self._processor = processor
        self._embedding_generator = embedding_generator

    async def execute(self, document_id: UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        document.start_processing()
        await self._repository.save(document)

        try:
            chunks = await self._processor.process(document)
            chunks = await self._generate_embeddings(chunks)
            document.mark_indexed(chunk_count=len(chunks))
            await self._repository.replace_chunks(document.id, chunks)
        except Exception as exc:
            document.mark_failed(str(exc))
            raise
        finally:
            await self._repository.save(document)

        return document

    async def _generate_embeddings(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if self._embedding_generator is None:
            return chunks

        embedded_chunks: list[DocumentChunk] = []
        for chunk in chunks:
            embedding = await self._embedding_generator.generate(chunk.content)
            embedded_chunks.append(
                DocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=embedding.values,
                    embedding_provider=embedding.provider,
                    embedding_model=embedding.model,
                    created_at=chunk.created_at,
                )
            )

        return embedded_chunks


def _sync_document_from_version(document: Document, version: DocumentVersion) -> None:
    document.version = version.version
    document.source_file_name = version.source_file_name
    document.content_type = version.content_type
    document.size_bytes = version.size_bytes
    document.storage_key = version.storage_key
    document.status = version.status
    document.chunk_count = version.chunk_count
    document.failure_reason = version.failure_reason
    document.last_processed_at = version.last_processed_at
    document.updated_at = version.updated_at
