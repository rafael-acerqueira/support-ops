from uuid import UUID, uuid4

import pytest

from supportops_api.application.documents import (
    ActivateDocument,
    CreateDocument,
    CreateDocumentInput,
    DeactivateDocument,
    DocumentNotFoundError,
    GeneratedEmbedding,
    GetDocument,
    ListDocumentChunks,
    ListDocuments,
    ProcessDocument,
)
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
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

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        self.chunks[document_id] = chunks


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
async def test_list_documents_returns_all_documents() -> None:
    repository = InMemoryDocumentRepository()
    document = create_uploaded_document()
    await repository.add(document)

    documents = await ListDocuments(repository).execute()

    assert documents == [document]


@pytest.mark.asyncio
async def test_get_document_raises_when_document_does_not_exist() -> None:
    repository = InMemoryDocumentRepository()
    document_id = uuid4()

    with pytest.raises(DocumentNotFoundError) as error:
        await GetDocument(repository).execute(document_id)

    assert error.value.document_id == document_id


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
