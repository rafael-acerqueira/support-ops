from __future__ import annotations

import os
from uuid import UUID

from celery import Celery
from dotenv import find_dotenv, load_dotenv

from supportops_api.application.documents import (
    DocumentNotFoundError,
    DocumentProcessingQueue,
    DocumentRepository,
    EnqueuedDocumentProcessing,
)

DOCUMENT_PROCESSING_TASK_NAME = "supportops.documents.process"

load_dotenv(find_dotenv(usecwd=True))


def get_broker_url() -> str:
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


celery_app = Celery("supportops_api", broker=get_broker_url())


class CeleryDocumentProcessingQueue(DocumentProcessingQueue):
    def __init__(self, repository: DocumentRepository, app: Celery = celery_app) -> None:
        self._repository = repository
        self._app = app

    async def enqueue(self, document_id: UUID) -> EnqueuedDocumentProcessing:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        result = self._app.send_task(DOCUMENT_PROCESSING_TASK_NAME, args=[str(document_id)])
        return EnqueuedDocumentProcessing(document_id=document_id, task_id=result.id)
