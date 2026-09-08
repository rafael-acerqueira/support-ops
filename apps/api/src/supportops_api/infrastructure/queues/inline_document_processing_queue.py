from __future__ import annotations

from uuid import UUID

from supportops_api.application.documents import (
    DocumentProcessingQueue,
    DocumentProcessor,
    DocumentRepository,
    DocumentVersionRepository,
    EmbeddingGenerator,
    EnqueuedDocumentProcessing,
    ProcessDocument,
)


class InlineDocumentProcessingQueue(DocumentProcessingQueue):
    def __init__(
        self,
        repository: DocumentRepository,
        processor: DocumentProcessor,
        embedding_generator: EmbeddingGenerator | None = None,
        version_repository: DocumentVersionRepository | None = None,
    ) -> None:
        self._repository = repository
        self._processor = processor
        self._embedding_generator = embedding_generator
        self._version_repository = version_repository

    async def enqueue(self, document_id: UUID) -> EnqueuedDocumentProcessing:
        await ProcessDocument(
            self._repository,
            self._processor,
            self._embedding_generator,
            self._version_repository,
        ).execute(document_id)
        return EnqueuedDocumentProcessing(
            document_id=document_id,
            task_id=f"inline:{document_id}",
        )
