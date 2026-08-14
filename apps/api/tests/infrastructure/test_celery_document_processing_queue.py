from uuid import UUID, uuid4

import pytest

from supportops_api.application.documents import DocumentNotFoundError
from supportops_api.domain.documents import Document, DocumentChunk, DocumentType, ProductArea
from supportops_api.infrastructure.queues.celery_document_processing_queue import (
    DOCUMENT_PROCESSING_TASK_NAME,
    CeleryDocumentProcessingQueue,
)


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[UUID, Document] = {}

    async def add(self, document: Document) -> None:
        self.documents[document.id] = document

    async def save(self, document: Document) -> None:
        self.documents[document.id] = document

    async def get(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    async def list_all(self) -> list[Document]:
        return list(self.documents.values())

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        pass


class FakeAsyncResult:
    id = "task-123"


class FakeCeleryApp:
    def __init__(self) -> None:
        self.sent_tasks: list[tuple[str, list[str]]] = []

    def send_task(self, name: str, args: list[str]):
        self.sent_tasks.append((name, args))
        return FakeAsyncResult()


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
async def test_celery_document_processing_queue_sends_task() -> None:
    repository = InMemoryDocumentRepository()
    document = create_document()
    await repository.add(document)
    celery_app = FakeCeleryApp()

    enqueued = await CeleryDocumentProcessingQueue(repository, celery_app).enqueue(document.id)

    assert enqueued.document_id == document.id
    assert enqueued.task_id == "task-123"
    assert celery_app.sent_tasks == [(DOCUMENT_PROCESSING_TASK_NAME, [str(document.id)])]


@pytest.mark.asyncio
async def test_celery_document_processing_queue_requires_existing_document() -> None:
    repository = InMemoryDocumentRepository()
    celery_app = FakeCeleryApp()
    document_id = uuid4()

    with pytest.raises(DocumentNotFoundError):
        await CeleryDocumentProcessingQueue(repository, celery_app).enqueue(document_id)

    assert celery_app.sent_tasks == []
