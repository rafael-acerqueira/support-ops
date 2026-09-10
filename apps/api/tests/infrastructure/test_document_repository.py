import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)
from supportops_api.infrastructure.database import get_database_url
from supportops_api.infrastructure.persistence.document_repository import (
    PostgresDocumentRepository,
    _chunk_replacement_version_id,
    _chunk_to_record,
    _current_or_legacy_chunk_version_filter,
    _document_to_record,
    _record_to_chunk,
    _record_to_document,
    _record_to_version,
    _version_to_record,
)
from supportops_api.infrastructure.persistence.models import (
    DocumentChunkRecord,
    DocumentRecord,
    DocumentVersionRecord,
    Vector,
)


def create_indexed_document() -> Document:
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        tags=("refund", "enterprise"),
        storage_key="documents/refund-policy.md",
    )
    document.start_processing()
    document.mark_indexed(chunk_count=2)
    return document


def create_indexed_document_version(document_id: UUID) -> DocumentVersion:
    version = DocumentVersion.create(
        document_id=document_id,
        version="v2",
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=2048,
        storage_key="documents/refund-policy/v2.md",
    )
    version.start_processing()
    version.mark_indexed(chunk_count=3)
    version.activate()
    return version


def create_test_embedding(value: float) -> tuple[float, ...]:
    return tuple(value for _ in range(1536))


def test_document_record_roundtrip_preserves_domain_values() -> None:
    document = create_indexed_document()
    document.current_version_id = uuid4()

    record = _document_to_record(document)
    mapped_document = _record_to_document(record)

    assert mapped_document.id == document.id
    assert mapped_document.name == "Refund Policy"
    assert mapped_document.document_type == DocumentType.INTERNAL_POLICY
    assert mapped_document.product_area == ProductArea.BILLING
    assert mapped_document.status == DocumentStatus.INDEXED
    assert mapped_document.tags == ("refund", "enterprise")
    assert mapped_document.storage_key == "documents/refund-policy.md"
    assert mapped_document.current_version_id == document.current_version_id
    assert mapped_document.chunk_count == 2
    assert mapped_document.last_processed_at == document.last_processed_at


def test_document_version_record_roundtrip_preserves_domain_values() -> None:
    document_id = uuid4()
    version = create_indexed_document_version(document_id)

    record = _version_to_record(version)
    mapped_version = _record_to_version(record)

    assert mapped_version.id == version.id
    assert mapped_version.document_id == document_id
    assert mapped_version.version == "v2"
    assert mapped_version.status == DocumentStatus.INDEXED
    assert mapped_version.is_active is True
    assert mapped_version.storage_key == "documents/refund-policy/v2.md"
    assert mapped_version.chunk_count == 3
    assert mapped_version.activated_at == version.activated_at
    assert mapped_version.last_processed_at == version.last_processed_at


def test_chunk_record_roundtrip_preserves_domain_values() -> None:
    version_id = uuid4()
    chunk = DocumentChunk(
        document_id=uuid4(),
        document_version_id=version_id,
        chunk_index=1,
        content="Enterprise refunds require approval.",
        metadata={"section": "Refund policy"},
        embedding=(0.1, -0.2, 0.3),
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )

    record = _chunk_to_record(chunk)
    mapped_chunk = _record_to_chunk(record)

    assert mapped_chunk.id == chunk.id
    assert mapped_chunk.document_id == chunk.document_id
    assert mapped_chunk.document_version_id == version_id
    assert mapped_chunk.chunk_index == 1
    assert mapped_chunk.content == "Enterprise refunds require approval."
    assert mapped_chunk.metadata == {"section": "Refund policy"}
    assert mapped_chunk.embedding == (0.1, -0.2, 0.3)
    assert mapped_chunk.embedding_provider == "openai"
    assert mapped_chunk.embedding_model == "text-embedding-3-small"


def test_chunk_replacement_version_id_returns_none_for_legacy_chunks() -> None:
    chunks = [DocumentChunk(document_id=uuid4(), chunk_index=0, content="Legacy chunk")]

    assert _chunk_replacement_version_id(chunks) is None


def test_chunk_replacement_version_id_returns_common_version() -> None:
    document_id = uuid4()
    version_id = uuid4()
    chunks = [
        DocumentChunk(
            document_id=document_id,
            document_version_id=version_id,
            chunk_index=0,
            content="First chunk",
        ),
        DocumentChunk(
            document_id=document_id,
            document_version_id=version_id,
            chunk_index=1,
            content="Second chunk",
        ),
    ]

    assert _chunk_replacement_version_id(chunks) == version_id


def test_current_or_legacy_chunk_version_filter_allows_current_versions_and_legacy_chunks() -> None:
    compiled = str(_current_or_legacy_chunk_version_filter().compile())

    assert "document_chunks.document_version_id IS NULL" in compiled
    assert "documents.current_version_id = document_chunks.document_version_id" in compiled
    assert "document_versions.status" in compiled


def test_vector_type_converts_python_values_to_pgvector_text() -> None:
    process = Vector(3).bind_processor(None)

    assert process((0.1, -0.2, 0.3)) == "[0.1,-0.2,0.3]"
    assert process(None) is None


def test_vector_type_converts_pgvector_text_to_python_values() -> None:
    process = Vector(3).result_processor(None, None)

    assert process("[0.1,-0.2,0.3]") == [0.1, -0.2, 0.3]
    assert process(None) is None


@pytest.mark.asyncio
async def test_replace_chunks_rejects_chunks_from_another_document() -> None:
    repository = PostgresDocumentRepository(session=None)  # type: ignore[arg-type]
    document_id = uuid4()
    chunks = [DocumentChunk(document_id=uuid4(), chunk_index=0, content="Wrong document")]

    with pytest.raises(ValueError, match="belong to the document"):
        await repository.replace_chunks(document_id, chunks)


@pytest.mark.asyncio
async def test_replace_chunks_rejects_chunks_from_multiple_document_versions() -> None:
    repository = PostgresDocumentRepository(session=None)  # type: ignore[arg-type]
    document_id = uuid4()
    chunks = [
        DocumentChunk(
            document_id=document_id,
            document_version_id=uuid4(),
            chunk_index=0,
            content="First version chunk",
        ),
        DocumentChunk(
            document_id=document_id,
            document_version_id=uuid4(),
            chunk_index=1,
            content="Second version chunk",
        ),
    ]

    with pytest.raises(ValueError, match="same document version"):
        await repository.replace_chunks(document_id, chunks)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SUPPORTOPS_RUN_DB_TESTS") != "1",
    reason="Set SUPPORTOPS_RUN_DB_TESTS=1 to run Postgres integration tests.",
)
async def test_postgres_document_repository_persists_document_workflow() -> None:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    document = create_indexed_document()
    document.deactivate()
    chunks = [
        DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content="First chunk",
            embedding=create_test_embedding(0.1),
            embedding_provider="deterministic",
            embedding_model="supportops-deterministic-v1",
        ),
        DocumentChunk(
            document_id=document.id,
            chunk_index=1,
            content="Second chunk",
            embedding=create_test_embedding(0.2),
            embedding_provider="deterministic",
            embedding_model="supportops-deterministic-v1",
        ),
    ]

    try:
        async with session_factory() as session:
            repository = PostgresDocumentRepository(session)
            await repository.add(document)
            await repository.replace_chunks(document.id, chunks)
            await session.commit()

        async with session_factory() as session:
            repository = PostgresDocumentRepository(session)
            stored = await repository.get(document.id)

            assert stored is not None
            assert stored.id == document.id
            assert stored.status == DocumentStatus.INDEXED
            assert stored.is_active is False

            stored.activate()
            await repository.save(stored)
            await session.commit()

        async with session_factory() as session:
            repository = PostgresDocumentRepository(session)
            documents = await repository.list_all()
            stored = await repository.get(document.id)

            assert document.id in {item.id for item in documents}
            assert stored is not None
            assert stored.is_active is True
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(DocumentChunkRecord).where(DocumentChunkRecord.document_id == document.id)
            )
            await session.execute(delete(DocumentRecord).where(DocumentRecord.id == document.id))
            await session.commit()
        await engine.dispose()
