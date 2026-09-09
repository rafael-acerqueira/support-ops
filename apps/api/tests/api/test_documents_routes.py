from collections.abc import AsyncIterator
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio

from src.main import app
from supportops_api.api.dependencies import (
    get_document_processing_queue,
    get_document_repository,
    get_document_storage,
    get_document_version_repository,
)
from supportops_api.application.documents import (
    DocumentNotFoundError,
    DocumentRepository,
    DocumentVersionRepository,
    EnqueuedDocumentProcessing,
    StoredDocumentFile,
)
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)
from supportops_api.infrastructure.database import get_session


class FakeDocumentProcessingQueue:
    def __init__(
        self,
        repository: InMemoryDocumentRepository,
        version_repository: InMemoryDocumentVersionRepository,
    ) -> None:
        self._repository = repository
        self._version_repository = version_repository
        self.should_fail = False
        self.enqueued_document_ids: list[UUID] = []

    async def enqueue(self, document_id: UUID) -> EnqueuedDocumentProcessing:
        self.enqueued_document_ids.append(document_id)
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        if self.should_fail:
            document.mark_failed("Document has no storage key")
            await self._mark_version_failed(document)
            await self._repository.save(document)
            raise ValueError("Document has no storage key")

        document.start_processing()
        version = await self._processing_version(document)
        if version is not None:
            version.start_processing()
            await self._version_repository.save(version)

        chunks = [
            DocumentChunk(
                document_id=document.id,
                document_version_id=version.id if version else None,
                chunk_index=0,
                content="First chunk",
            ),
            DocumentChunk(
                document_id=document.id,
                document_version_id=version.id if version else None,
                chunk_index=1,
                content="Second chunk",
            ),
        ]
        document.mark_indexed(chunk_count=len(chunks))
        if version is not None:
            version.mark_indexed(chunk_count=len(chunks))
            await self._version_repository.deactivate_all_for_document(document.id)
            version.activate()
            await self._version_repository.save(version)

        await self._repository.replace_chunks(document.id, chunks)
        await self._repository.save(document)
        return EnqueuedDocumentProcessing(
            document_id=document.id,
            task_id=f"fake:{document.id}",
        )

    async def _processing_version(self, document: Document) -> DocumentVersion | None:
        if document.storage_key is None:
            return None

        return await self._version_repository.get_for_document_snapshot(
            document.id,
            document.version,
            document.storage_key,
        )

    async def _mark_version_failed(self, document: Document) -> None:
        version = await self._processing_version(document)
        if version is None:
            return

        version.mark_failed("Document has no storage key")
        await self._version_repository.save(version)


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

    async def list_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        return self.chunks.get(document_id, [])

    async def list_chunks_for_version(
        self, document_id: UUID, document_version_id: UUID
    ) -> list[DocumentChunk]:
        return [
            chunk
            for chunk in self.chunks.get(document_id, [])
            if chunk.document_version_id == document_version_id
        ]

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        self.chunks[document_id] = chunks


class InMemoryDocumentVersionRepository(DocumentVersionRepository):
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

    async def get_for_document_snapshot(
        self, document_id: UUID, version_label: str, storage_key: str
    ) -> DocumentVersion | None:
        for version in self.versions.values():
            if (
                version.document_id == document_id
                and version.version == version_label
                and version.storage_key == storage_key
            ):
                return version

        return None

    async def deactivate_all_for_document(self, document_id: UUID) -> None:
        for version in self.versions.values():
            if version.document_id == document_id:
                version.deactivate()


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
    version_repository = InMemoryDocumentVersionRepository()
    storage = InMemoryDocumentStorage()
    processing_queue = FakeDocumentProcessingQueue(repository, version_repository)
    session = FakeSession()

    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_document_version_repository] = lambda: version_repository
    app.dependency_overrides[get_document_storage] = lambda: storage
    app.dependency_overrides[get_document_processing_queue] = lambda: processing_queue
    app.dependency_overrides[get_session] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repository, version_repository, storage, processing_queue, session

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


def create_indexed_version(
    repository: InMemoryDocumentVersionRepository,
    document_id: UUID,
    version_label: str = "v2",
) -> DocumentVersion:
    version = DocumentVersion.create(
        document_id=document_id,
        version=version_label,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key=f"documents/refund-policy/{version_label}.md",
    )
    version.start_processing()
    version.mark_indexed(chunk_count=3)
    repository.versions[version.id] = version
    return version


@pytest.mark.asyncio
async def test_create_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, session = api_client

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
    client, repository, _version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)

    response = await client.get("/api/documents")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(document.id)


@pytest.mark.asyncio
async def test_list_documents_uses_document_version_processing_fields(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    version = create_indexed_version(version_repository, document.id)
    document.version = version.version
    document.storage_key = version.storage_key

    response = await client.get("/api/documents")

    body = response.json()
    assert response.status_code == 200
    assert body[0]["id"] == str(document.id)
    assert body[0]["version"] == "v2"
    assert body[0]["status"] == "indexed"
    assert body[0]["chunk_count"] == 3
    assert body[0]["storage_key"] == "documents/refund-policy/v2.md"


@pytest.mark.asyncio
async def test_get_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)

    response = await client.get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_document_uses_document_version_processing_fields(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    version = create_indexed_version(version_repository, document.id)
    document.version = version.version
    document.storage_key = version.storage_key

    response = await client.get(f"/api/documents/{document.id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == str(document.id)
    assert body["version"] == "v2"
    assert body["status"] == "indexed"
    assert body["chunk_count"] == 3
    assert body["storage_key"] == "documents/refund-policy/v2.md"


@pytest.mark.asyncio
async def test_get_document_returns_404(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, _repository, _version_repository, _storage, _processing_queue, _session = api_client
    document_id = uuid4()

    response = await client.get(f"/api/documents/{document_id}")

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)


@pytest.mark.asyncio
async def test_list_document_chunks(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        content="Refund requests must include a reason.",
        embedding=(0.1, -0.2),
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    repository.chunks[document.id] = [chunk]

    response = await client.get(f"/api/documents/{document.id}/chunks")

    body = response.json()
    assert response.status_code == 200
    assert body[0]["id"] == str(chunk.id)
    assert body[0]["has_embedding"] is True
    assert body[0]["embedding_provider"] == "openai"
    assert body[0]["embedding_model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_list_document_versions(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    version = create_indexed_version(version_repository, document.id)

    response = await client.get(f"/api/documents/{document.id}/versions")

    body = response.json()
    assert response.status_code == 200
    assert body[0]["id"] == str(version.id)
    assert body[0]["document_id"] == str(document.id)
    assert body[0]["version"] == "v2"
    assert body[0]["status"] == "indexed"
    assert body[0]["is_active"] is False
    assert body[0]["storage_key"] == "documents/refund-policy/v2.md"


@pytest.mark.asyncio
async def test_list_document_versions_returns_404(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, _repository, _version_repository, _storage, _processing_queue, _session = api_client
    document_id = uuid4()

    response = await client.get(f"/api/documents/{document_id}/versions")

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)


@pytest.mark.asyncio
async def test_list_document_version_chunks(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    version = create_indexed_version(version_repository, document.id)
    chunk = DocumentChunk(
        document_id=document.id,
        document_version_id=version.id,
        chunk_index=0,
        content="Refund requests must include a reason.",
        embedding=(0.1, -0.2),
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    repository.chunks[document.id] = [chunk]

    response = await client.get(f"/api/documents/{document.id}/versions/{version.id}/chunks")

    body = response.json()
    assert response.status_code == 200
    assert body[0]["id"] == str(chunk.id)
    assert body[0]["document_version_id"] == str(version.id)
    assert body[0]["has_embedding"] is True


@pytest.mark.asyncio
async def test_list_document_version_chunks_returns_404_for_wrong_version(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, _session = api_client
    document = create_document(repository)
    version = create_indexed_version(version_repository, uuid4())

    response = await client.get(f"/api/documents/{document.id}/versions/{version.id}/chunks")

    assert response.status_code == 404
    assert response.json()["detail"]["document_version_id"] == str(version.id)


@pytest.mark.asyncio
async def test_list_document_chunks_returns_404(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, _repository, _version_repository, _storage, _processing_queue, _session = api_client
    document_id = uuid4()

    response = await client.get(f"/api/documents/{document_id}/chunks")

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)


@pytest.mark.asyncio
async def test_activate_and_deactivate_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, session = api_client
    document = create_document(repository)

    deactivate_response = await client.post(f"/api/documents/{document.id}/deactivate")
    activate_response = await client.post(f"/api/documents/{document.id}/activate")

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_activate_document_version(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, processing_queue, session = api_client
    document = create_document(repository)
    old_version = create_indexed_version(version_repository, document.id, "v1")
    old_version.activate()
    version = create_indexed_version(version_repository, document.id, "v2")

    response = await client.post(f"/api/documents/{document.id}/versions/{version.id}/activate")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == str(version.id)
    assert body["is_active"] is True
    assert old_version.is_active is False
    assert repository.documents[document.id].version == "v2"
    assert repository.documents[document.id].storage_key == "documents/refund-policy/v2.md"
    assert processing_queue.enqueued_document_ids == [document.id]
    assert len(repository.chunks[document.id]) == 2
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_activate_document_version_returns_404_for_wrong_version(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, session = api_client
    document = create_document(repository)
    version_id = uuid4()

    response = await client.post(f"/api/documents/{document.id}/versions/{version_id}/activate")

    assert response.status_code == 404
    assert response.json()["detail"]["document_version_id"] == str(version_id)
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_activate_document_version_returns_400_when_version_is_not_indexed(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, _storage, _processing_queue, session = api_client
    document = create_document(repository)
    version = DocumentVersion.create(
        document_id=document.id,
        version="v2",
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key="documents/refund-policy/v2.md",
    )
    version_repository.versions[version.id] = version

    response = await client.post(f"/api/documents/{document.id}/versions/{version.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Only indexed document versions can be activated"
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_upload_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, storage, _processing_queue, session = api_client

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
    assert body["status"] == "indexed"
    assert body["chunk_count"] == 2
    document_id = UUID(body["id"])
    assert document_id in repository.documents
    versions = await version_repository.list_for_document(document_id)
    assert len(versions) == 1
    assert versions[0].document_id == document_id
    assert versions[0].version == "v1"
    assert versions[0].storage_key == "fake/enterprise-sla.md"
    assert repository.documents[document_id].status == DocumentStatus.INDEXED
    assert len(repository.chunks[document_id]) == 2
    assert storage.saved_files == [("enterprise-sla.md", "text/markdown", b"SLA policy content")]
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_upload_document_returns_400_for_empty_file(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, storage, _processing_queue, session = api_client

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
async def test_upload_document_version(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, version_repository, storage, _processing_queue, session = api_client
    document = create_document(repository)
    current_version = create_indexed_version(version_repository, document.id, "v1")
    current_version.activate()

    response = await client.post(
        f"/api/documents/{document.id}/versions/upload",
        files={"file": ("refund-policy-v2.md", b"Updated refund policy content", "text/markdown")},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["document_id"] == str(document.id)
    assert body["version"] == "v2"
    assert body["source_file_name"] == "refund-policy-v2.md"
    assert body["storage_key"] == "fake/refund-policy-v2.md"
    assert repository.documents[document.id].version == "v2"
    assert repository.documents[document.id].storage_key == "fake/refund-policy-v2.md"
    assert repository.documents[document.id].status == DocumentStatus.INDEXED
    assert len(repository.chunks[document.id]) == 2
    assert storage.saved_files == [
        ("refund-policy-v2.md", "text/markdown", b"Updated refund policy content")
    ]
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_upload_document_version_returns_404_for_missing_document(
    api_client: tuple[
        httpx.AsyncClient, InMemoryDocumentRepository, InMemoryDocumentStorage, FakeSession
    ],
) -> None:
    client, repository, _version_repository, storage, _processing_queue, session = api_client
    document_id = uuid4()

    response = await client.post(
        f"/api/documents/{document_id}/versions/upload",
        files={"file": ("refund-policy-v2.md", b"Updated refund policy content", "text/markdown")},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["document_id"] == str(document_id)
    assert repository.documents == {}
    assert storage.saved_files == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_process_document(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryDocumentRepository,
        InMemoryDocumentStorage,
        FakeDocumentProcessingQueue,
        FakeSession,
    ],
) -> None:
    client, repository, _version_repository, _storage, _processing_queue, session = api_client
    document = create_document(repository)

    response = await client.post(f"/api/documents/{document.id}/process")

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "queued"
    assert body["task_id"] == f"fake:{document.id}"
    assert body["document_id"] == str(document.id)
    assert repository.documents[document.id].status == DocumentStatus.INDEXED
    assert len(repository.chunks[document.id]) == 2
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_process_document_returns_400_when_processing_fails(
    api_client: tuple[
        httpx.AsyncClient,
        InMemoryDocumentRepository,
        InMemoryDocumentStorage,
        FakeDocumentProcessingQueue,
        FakeSession,
    ],
) -> None:
    client, repository, _version_repository, _storage, processing_queue, session = api_client
    processing_queue.should_fail = True
    document = create_document(repository)

    response = await client.post(f"/api/documents/{document.id}/process")

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Document has no storage key"
    assert repository.documents[document.id].status == DocumentStatus.FAILED
    assert session.commit_count == 1
