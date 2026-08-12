from __future__ import annotations

from uuid import UUID

from supportops_api.application.documents import (
    DocumentProcessingQueue,
    DocumentProcessor,
    DocumentRepository,
    ProcessDocument,
)
from supportops_api.domain.documents import Document


class InlineDocumentProcessingQueue(DocumentProcessingQueue):
    def __init__(self, repository: DocumentRepository, processor: DocumentProcessor) -> None:
        self._repository = repository
        self._processor = processor

    async def enqueue(self, document_id: UUID) -> Document:
        return await ProcessDocument(self._repository, self._processor).execute(document_id)
