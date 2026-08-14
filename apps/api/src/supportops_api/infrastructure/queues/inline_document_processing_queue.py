from __future__ import annotations

from uuid import UUID

from supportops_api.application.documents import (
    DocumentProcessingQueue,
    EnqueuedDocumentProcessing,
    DocumentProcessor,
    DocumentRepository,
    ProcessDocument,
)


class InlineDocumentProcessingQueue(DocumentProcessingQueue):
    def __init__(self, repository: DocumentRepository, processor: DocumentProcessor) -> None:
        self._repository = repository
        self._processor = processor

    async def enqueue(self, document_id: UUID) -> EnqueuedDocumentProcessing:
        await ProcessDocument(self._repository, self._processor).execute(document_id)
        return EnqueuedDocumentProcessing(
            document_id=document_id,
            task_id=f"inline:{document_id}",
        )
