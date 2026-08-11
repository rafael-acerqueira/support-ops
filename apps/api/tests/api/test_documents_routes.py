from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio

from src.main import app
from supportops_api.api.dependencies import get_document_repository
from supportops_api.application.documents import DocumentRepository
from supportops_api.domain.documents import Document, DocumentChunk, DocumentType, ProductArea
from supportops_api.infrastructure.database import get_session


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


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
async def api_client() -> (
    AsyncIterator[tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession]]
):
    repository = InMemoryDocumentRepository()
    session = FakeSession()

    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_session] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repository, session

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
    api_client: tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession],
) -> None:
    client, repository, session = api_client

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
    api_client: tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession],
) -> None:
    client, repository, _session = api_client
    document = create_document(repository)

    response = await client.get("/api/documents")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_document(
    api_client: tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession],
) -> None:
    client, repository, _session = api_client
    document = create_document(repository)

    response = await client.get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_document_returns_404(
    api_client: tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession],
) -> None:
    client, _repository, _session = api_client
    document_id = uuid4()

    response = await client.get(f"/api/documents/{document_id}")

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)


@pytest.mark.asyncio
async def test_activate_and_deactivate_document(
    api_client: tuple[httpx.AsyncClient, InMemoryDocumentRepository, FakeSession],
) -> None:
    client, repository, session = api_client
    document = create_document(repository)

    deactivate_response = await client.post(f"/api/documents/{document.id}/deactivate")
    activate_response = await client.post(f"/api/documents/{document.id}/activate")

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True
    assert session.commit_count == 2
