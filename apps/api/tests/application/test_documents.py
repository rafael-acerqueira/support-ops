from copy import copy
from uuid import UUID, uuid4

import pytest

from supportops_api.application.documents import (
    ActivateDocument,
    ActivateDocumentVersion,
    CreateDocument,
    CreateDocumentInput,
    CreateDocumentVersion,
    CreateDocumentVersionInput,
    DeactivateDocument,
    DocumentNotFoundError,
    DocumentVersionNotFoundError,
    GeneratedEmbedding,
    GetDocument,
    ListDocumentChunks,
    ListDocumentVersionChunks,
    ListDocumentVersions,
    ListDocuments,
    ProcessDocument,
)
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[UUID, Document] = {}
        self.chunks: dict[UUID, list[DocumentChunk]] = {}
        self.saved_documents: list[Document] = []

    async def add(self, document: Document) -> None:
        self.documents[document.id] = document

    async def save(self, document: Document) -> None:
        self.documents[document.id] = document
        self.saved_documents.append(document)

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


class InMemoryDocumentVersionRepository:
    def __init__(self) -> None:
        self.versions: dict[UUID, DocumentVersion] = {}
        self.saved_versions: list[DocumentVersion] = []

    async def add(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version

    async def save(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version
        self.saved_versions.append(copy(version))

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


class SuccessfulDocumentProcessor:
    async def process(self, document: Document) -> list[DocumentChunk]:
        return [
            DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                content="Refund requests must include a reason.",
            ),
            DocumentChunk(
                document_id=document.id,
                chunk_index=1,
                content="Enterprise refunds require approval.",
            ),
        ]


class FailingDocumentProcessor:
    async def process(self, document: Document) -> list[DocumentChunk]:
        raise RuntimeError("Parser failed")


class FakeEmbeddingGenerator:
    async def generate(self, text: str) -> GeneratedEmbedding:
        return GeneratedEmbedding(values=(float(len(text)),), model="fake-model", provider="fake")


class FailingEmbeddingGenerator:
    async def generate(self, text: str) -> GeneratedEmbedding:
        raise RuntimeError("Embedding provider failed")


def create_uploaded_document() -> Document:
    return Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
    )


def create_indexed_version(document_id: UUID, version: str = "v2") -> DocumentVersion:
    document_version = DocumentVersion.create(
        document_id=document_id,
        version=version,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key=f"documents/refund-policy/{version}.md",
    )
    document_version.start_processing()
    document_version.mark_indexed(chunk_count=3)
    return document_version


@pytest.mark.asyncio
async def test_create_document_persists_uploaded_document() -> None:
    repository = InMemoryDocumentRepository()
    use_case = CreateDocument(repository)

    document = await use_case.execute(
        CreateDocumentInput(
            name="Refund Policy",
            document_type=DocumentType.INTERNAL_POLICY,
            product_area=ProductArea.BILLING,
            source_file_name="refund-policy.md",
            content_type="text/markdown",
            size_bytes=1024,
            tags=("refund", "enterprise"),
            storage_key="documents/refund-policy.md",
        )
    )

    assert repository.documents[document.id] == document
    assert document.status == DocumentStatus.UPLOADED
    assert document.tags == ("refund", "enterprise")
    assert document.storage_key == "documents/refund-policy.md"


@pytest.mark.asyncio
async def test_create_document_version_persists_uploaded_version() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    await document_repository.add(document)

    version = await CreateDocumentVersion(document_repository, version_repository).execute(
        CreateDocumentVersionInput(
            document_id=document.id,
            version="v2",
            source_file_name="refund-policy.md",
            content_type="text/markdown",
            size_bytes=2048,
            storage_key="documents/refund-policy/v2.md",
        )
    )

    assert version_repository.versions[version.id] == version
    assert version.document_id == document.id
    assert version.version == "v2"
    assert version.status == DocumentStatus.UPLOADED
    assert document_repository.documents[document.id].current_version_id == version.id
    assert document_repository.documents[document.id].version == "v2"
    assert document_repository.documents[document.id].storage_key == "documents/refund-policy/v2.md"


@pytest.mark.asyncio
async def test_create_document_version_uses_next_version_label_when_not_provided() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    await document_repository.add(document)
    await version_repository.add(create_indexed_version(document.id, "v1"))
    await version_repository.add(create_indexed_version(document.id, "v2"))

    version = await CreateDocumentVersion(document_repository, version_repository).execute(
        CreateDocumentVersionInput(
            document_id=document.id,
            source_file_name="refund-policy.md",
            content_type="text/markdown",
            size_bytes=4096,
            storage_key="documents/refund-policy/v3.md",
        )
    )

    assert version.version == "v3"
    assert document_repository.documents[document.id].current_version_id == version.id
    assert document_repository.documents[document.id].version == "v3"
    assert document_repository.documents[document.id].status == DocumentStatus.UPLOADED


@pytest.mark.asyncio
async def test_create_document_version_requires_existing_document() -> None:
    with pytest.raises(DocumentNotFoundError):
        await CreateDocumentVersion(
            InMemoryDocumentRepository(),
            InMemoryDocumentVersionRepository(),
        ).execute(
            CreateDocumentVersionInput(
                document_id=uuid4(),
                version="v2",
                source_file_name="refund-policy.md",
                content_type="text/markdown",
                size_bytes=2048,
                storage_key="documents/refund-policy/v2.md",
            )
        )


@pytest.mark.asyncio
async def test_list_documents_returns_all_documents() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    documents = await ListDocuments(repository).execute()

    assert documents == [document]


@pytest.mark.asyncio
async def test_list_document_versions_returns_versions_for_document() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    version = create_indexed_version(document.id)
    await document_repository.add(document)
    await version_repository.add(version)

    versions = await ListDocumentVersions(document_repository, version_repository).execute(
        document.id
    )

    assert versions == [version]


@pytest.mark.asyncio
async def test_get_document_raises_when_document_does_not_exist() -> None:
    repository = InMemoryDocumentRepository()
    document_id = uuid4()

    with pytest.raises(DocumentNotFoundError) as error:
        await GetDocument(repository).execute(document_id)

    assert error.value.document_id == document_id


@pytest.mark.asyncio
async def test_activate_document_version_updates_active_version_and_document_snapshot() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    old_version = create_indexed_version(document.id, "v1")
    old_version.activate()
    new_version = create_indexed_version(document.id, "v2")
    await document_repository.add(document)
    await version_repository.add(old_version)
    await version_repository.add(new_version)

    activated = await ActivateDocumentVersion(document_repository, version_repository).execute(
        document.id, new_version.id
    )

    assert activated == new_version
    assert activated.is_active is True
    assert old_version.is_active is False
    assert document.current_version_id == new_version.id
    assert document.version == "v2"
    assert document.storage_key == "documents/refund-policy/v2.md"
    assert document.status == DocumentStatus.INDEXED
    assert document.chunk_count == 3
    assert version_repository.saved_versions == [new_version]
    assert document_repository.saved_documents == [document]


@pytest.mark.asyncio
async def test_activate_document_version_rejects_version_from_another_document() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    version = create_indexed_version(uuid4())
    await document_repository.add(document)
    await version_repository.add(version)

    with pytest.raises(DocumentVersionNotFoundError):
        await ActivateDocumentVersion(document_repository, version_repository).execute(
            document.id, version.id
        )


@pytest.mark.asyncio
async def test_list_document_chunks_returns_document_chunks() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    chunks = [DocumentChunk(document_id=document.id, chunk_index=0, content="Refund policy")]
    await repository.add(document)
    await repository.replace_chunks(document.id, chunks)

    listed_chunks = await ListDocumentChunks(repository).execute(document.id)

    assert listed_chunks == chunks


@pytest.mark.asyncio
async def test_list_document_chunks_prefers_current_version_chunks() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    current_version_id = uuid4()
    previous_version_id = uuid4()
    document.current_version_id = current_version_id
    chunks = [
        DocumentChunk(
            document_id=document.id,
            document_version_id=previous_version_id,
            chunk_index=0,
            content="Previous refund policy",
        ),
        DocumentChunk(
            document_id=document.id,
            document_version_id=current_version_id,
            chunk_index=0,
            content="Current refund policy",
        ),
    ]
    await repository.add(document)
    await repository.replace_chunks(document.id, chunks)

    listed_chunks = await ListDocumentChunks(repository).execute(document.id)

    assert listed_chunks == [chunks[1]]


@pytest.mark.asyncio
async def test_list_document_version_chunks_returns_chunks_for_version() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    version = create_indexed_version(document.id)
    other_version = create_indexed_version(document.id, "v3")
    chunks = [
        DocumentChunk(
            document_id=document.id,
            document_version_id=version.id,
            chunk_index=0,
            content="Refund policy",
        ),
        DocumentChunk(
            document_id=document.id,
            document_version_id=other_version.id,
            chunk_index=0,
            content="Other refund policy",
        ),
    ]
    await document_repository.add(document)
    await version_repository.add(version)
    await version_repository.add(other_version)
    await document_repository.replace_chunks(document.id, chunks)

    listed_chunks = await ListDocumentVersionChunks(
        document_repository, version_repository
    ).execute(document.id, version.id)

    assert listed_chunks == [chunks[0]]


@pytest.mark.asyncio
async def test_list_document_version_chunks_rejects_version_from_another_document() -> None:
    document_repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = create_uploaded_document()
    version = create_indexed_version(uuid4())
    await document_repository.add(document)
    await version_repository.add(version)

    with pytest.raises(DocumentVersionNotFoundError):
        await ListDocumentVersionChunks(document_repository, version_repository).execute(
            document.id, version.id
        )


@pytest.mark.asyncio
async def test_activate_and_deactivate_document() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    deactivated = await DeactivateDocument(repository).execute(document.id)
    assert deactivated.is_active is False

    activated = await ActivateDocument(repository).execute(document.id)
    assert activated.is_active is True


@pytest.mark.asyncio
async def test_process_document_replaces_chunks_and_marks_document_indexed() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    processed = await ProcessDocument(repository, SuccessfulDocumentProcessor()).execute(
        document.id
    )

    assert processed.status == DocumentStatus.INDEXED
    assert processed.chunk_count == 2
    assert len(repository.chunks[document.id]) == 2


@pytest.mark.asyncio
async def test_process_document_syncs_current_version_when_version_repository_is_provided() -> None:
    repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        storage_key="documents/refund-policy/v1.md",
    )
    version = DocumentVersion.create(
        document_id=document.id,
        version=document.version,
        source_file_name=document.source_file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        storage_key=document.storage_key or "",
    )
    await repository.add(document)
    await version_repository.add(version)

    await ProcessDocument(
        repository,
        SuccessfulDocumentProcessor(),
        version_repository=version_repository,
    ).execute(document.id)

    assert version.status == DocumentStatus.INDEXED
    assert version.is_active is True
    assert document.current_version_id == version.id
    assert version.chunk_count == 2
    assert version.last_processed_at is not None
    assert [chunk.document_version_id for chunk in repository.chunks[document.id]] == [
        version.id,
        version.id,
    ]
    assert version_repository.saved_versions[0].status == DocumentStatus.PROCESSING
    assert version_repository.saved_versions[1].status == DocumentStatus.INDEXED
    assert len(version_repository.saved_versions) == 2


@pytest.mark.asyncio
async def test_process_document_uses_document_snapshot_version() -> None:
    repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy-v2.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key="documents/refund-policy/v2.md",
    )
    document.version = "v2"
    active_version = create_indexed_version(document.id, "v1")
    active_version.activate()
    uploaded_version = DocumentVersion.create(
        document_id=document.id,
        version="v2",
        source_file_name=document.source_file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        storage_key=document.storage_key or "",
    )
    await repository.add(document)
    await version_repository.add(active_version)
    await version_repository.add(uploaded_version)

    await ProcessDocument(
        repository,
        SuccessfulDocumentProcessor(),
        version_repository=version_repository,
    ).execute(document.id)

    assert uploaded_version.status == DocumentStatus.INDEXED
    assert uploaded_version.is_active is True
    assert active_version.is_active is False
    assert document.current_version_id == uploaded_version.id
    assert [chunk.document_version_id for chunk in repository.chunks[document.id]] == [
        uploaded_version.id,
        uploaded_version.id,
    ]


@pytest.mark.asyncio
async def test_process_document_prefers_current_version_id() -> None:
    repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy-v2.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key="documents/refund-policy/v2.md",
    )
    document.version = "v2"
    snapshot_match = DocumentVersion.create(
        document_id=document.id,
        version="v2",
        source_file_name=document.source_file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        storage_key=document.storage_key or "",
    )
    current_version = DocumentVersion.create(
        document_id=document.id,
        version="v3",
        source_file_name="refund-policy-v3.md",
        content_type="text/markdown",
        size_bytes=4096,
        storage_key="documents/refund-policy/v3.md",
    )
    document.current_version_id = current_version.id
    await repository.add(document)
    await version_repository.add(snapshot_match)
    await version_repository.add(current_version)

    await ProcessDocument(
        repository,
        SuccessfulDocumentProcessor(),
        version_repository=version_repository,
    ).execute(document.id)

    assert current_version.status == DocumentStatus.INDEXED
    assert snapshot_match.status == DocumentStatus.UPLOADED
    assert document.current_version_id == current_version.id
    assert document.version == "v3"
    assert [chunk.document_version_id for chunk in repository.chunks[document.id]] == [
        current_version.id,
        current_version.id,
    ]


@pytest.mark.asyncio
async def test_process_document_marks_current_version_processing_before_work() -> None:
    repository = InMemoryDocumentRepository()
    version_repository = InMemoryDocumentVersionRepository()
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        storage_key="documents/refund-policy/v1.md",
    )
    version = DocumentVersion.create(
        document_id=document.id,
        version=document.version,
        source_file_name=document.source_file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        storage_key=document.storage_key or "",
    )
    await repository.add(document)
    await version_repository.add(version)

    with pytest.raises(RuntimeError, match="Parser failed"):
        await ProcessDocument(
            repository,
            FailingDocumentProcessor(),
            version_repository=version_repository,
        ).execute(document.id)

    assert version_repository.saved_versions[0].status == DocumentStatus.PROCESSING
    assert version_repository.saved_versions[1].status == DocumentStatus.FAILED
    assert version_repository.saved_versions[1].failure_reason == "Parser failed"
    assert document.current_version_id == version.id
    assert len(version_repository.saved_versions) == 2


@pytest.mark.asyncio
async def test_process_document_generates_chunk_embeddings_when_generator_is_provided() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    await ProcessDocument(
        repository,
        SuccessfulDocumentProcessor(),
        FakeEmbeddingGenerator(),
    ).execute(document.id)

    chunks = repository.chunks[document.id]
    assert chunks[0].embedding == (38.0,)
    assert chunks[0].embedding_provider == "fake"
    assert chunks[0].embedding_model == "fake-model"
    assert chunks[1].embedding == (36.0,)
    assert chunks[1].embedding_provider == "fake"
    assert chunks[1].embedding_model == "fake-model"


@pytest.mark.asyncio
async def test_process_document_marks_failed_when_embedding_generation_fails() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    with pytest.raises(RuntimeError, match="Embedding provider failed"):
        await ProcessDocument(
            repository,
            SuccessfulDocumentProcessor(),
            FailingEmbeddingGenerator(),
        ).execute(document.id)

    assert document.status == DocumentStatus.FAILED
    assert document.failure_reason == "Embedding provider failed"
    assert repository.chunks.get(document.id) is None


@pytest.mark.asyncio
async def test_process_document_marks_failed_when_processor_fails() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    with pytest.raises(RuntimeError, match="Parser failed"):
        await ProcessDocument(repository, FailingDocumentProcessor()).execute(document.id)

    assert document.status == DocumentStatus.FAILED
    assert document.failure_reason == "Parser failed"
