from collections.abc import AsyncIterator
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio

from src.main import app
from supportops_api.api.dependencies import (
    get_document_processor,
    get_document_repository,
    get_document_storage,
)
from supportops_api.application.documents import DocumentRepository, StoredDocumentFile
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    ProductArea,
)
from supportops_api.infrastructure.database import get_session


class FakeDocumentProcessor:
    def __init__(self) -> None:
        self.should_fail = False

    async def process(self, document: Document) -> list[DocumentChunk]:
        if self.should_fail:
            raise ValueError("Document has no storage key")

        return [
            DocumentChunk(document_id=document.id, chunk_index=0, content="First chunk"),
            DocumentChunk(document_id=document.id, chunk_index=1, content="Second chunk"),
        ]


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class InMemoryDocumentStorage:
    def __init__(self) -> None:
        self.saved_files: list[tuple[str, str, bytes]] = []

    async def save(
        self,
        *,
        file_name: str,
        content_type: str,
        content,
    ) -> StoredDocumentFile:
        data = content.read()
        if not data:
            raise ValueError("Document file cannot be empty")

        self.saved_files.append((file_name, content_type, data))
        return StoredDocumentFile(
            storage_key=f"fake/{file_name}",
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(data),
        )

    async def open(self, storage_key: str):
        for file_name, _content_type, data in self.saved_files:
            if storage_key == f"fake/{file_name}":
                return BytesIO(data)

        raise FileNotFoundError(storage_key)


class InMemoryDocumentRepository(DocumentRepository):
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


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[
    tuple[
        httpx.AsyncClient,
        InMemoryDocumentRepository,
        InMemoryDocumentStorage,
        FakeSession,
    ]
]:
    repository = InMemoryDocumentRepository()
    storage = InMemoryDocumentStorage()
    processor = FakeDocumentProcessor()
    session = FakeSession()

    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_document_storage] = lambda: storage
    app.dependency_overrides[get_document_processor] = lambda: processor
    app.dependency_overrides[get_session] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repository, storage, processor, session

    app.dependency_overrides.clear()


def create_document(repository: InMemoryDocumentRepository) -> Document:
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
    )
    repository.documents[document.id] = document
    return document


@pytest.mark.asyncio
async def test_create_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _storage, _processor, session = api_client

    response = await client.post(
        "/api/documents",
        json={
            "name": " Refund Policy ",
            "document_type": "internal_policy",
            "product_area": "billing",
            "source_file_name": "refund-policy.md",
            "content_type": "text/markdown",
            "size_bytes": 1024,
            "tags": ["Enterprise", "refund", "REFUND"],
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["name"] == "Refund Policy"
    assert body["status"] == "uploaded"
    assert body["tags"] == ["enterprise", "refund"]
    assert UUID(body["id"]) in repository.documents
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_list_documents(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _storage, _processor, _session = api_client
    document = create_document(repository)

    response = await client.get("/api/documents")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _storage, _processor, _session = api_client
    document = create_document(repository)

    response = await client.get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_document_returns_404(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, _repository, _storage, _processor, _session = api_client
    document_id = uuid4()

    response = await client.get(f"/api/documents/{document_id}")

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)


@pytest.mark.asyncio
async def test_activate_and_deactivate_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _storage, _processor, session = api_client
    document = create_document(repository)

    deactivate_response = await client.post(f"/api/documents/{document.id}/deactivate")
    activate_response = await client.post(f"/api/documents/{document.id}/activate")

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_upload_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, storage, _processor, session = api_client

    response = await client.post(
        "/api/documents/upload",
        data={
            "document_type": "sla_policy",
            "product_area": "support",
            "tags": ["enterprise", "sla"],
        },
        files={"file": ("enterprise-sla.md", b"SLA policy content", "text/markdown")},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["name"] == "enterprise-sla.md"
    assert body["document_type"] == "sla_policy"
    assert body["product_area"] == "support"
    assert body["size_bytes"] == len(b"SLA policy content")
    assert body["tags"] == ["enterprise", "sla"]
    assert body["storage_key"] == "fake/enterprise-sla.md"
    assert UUID(body["id"]) in repository.documents
    assert storage.saved_files == [("enterprise-sla.md", "text/markdown", b"SLA policy content")]
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_upload_document_returns_400_for_empty_file(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, storage, _processor, session = api_client

    response = await client.post(
        "/api/documents/upload",
        data={"document_type": "faq", "product_area": "support"},
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Document file cannot be empty"
    assert repository.documents == {}
    assert storage.saved_files == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_process_document(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryDocumentRepository,
        InMemoryDocumentStorage,
        FakeDocumentProcessor,
        FakeSession,
    ],
) -> None:
    client, repository, _storage, _processor, session = api_client
    document = create_document(repository)

    response = await client.post(f"/api/documents/{document.id}/process")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "indexed"
    assert body["chunk_count"] == 2
    assert repository.documents[document.id].status == DocumentStatus.INDEXED
    assert len(repository.chunks[document.id]) == 2
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_process_document_returns_400_when_processing_fails(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryDocumentRepository,
        InMemoryDocumentStorage,
        FakeDocumentProcessor,
        FakeSession,
    ],
) -> None:
    client, repository, _storage, processor, session = api_client
    processor.should_fail = True
    document = create_document(repository)

    response = await client.post(f"/api/documents/{document.id}/process")

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Document has no storage key"
    assert repository.documents[document.id].status == DocumentStatus.FAILED
    assert session.commit_count == 1
