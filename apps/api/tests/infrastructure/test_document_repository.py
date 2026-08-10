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
    ProductArea,
)
from supportops_api.infrastructure.database import get_database_url
from supportops_api.infrastructure.persistence.document_repository import (
    PostgresDocumentRepository,
    _chunk_to_record,
    _document_to_record,
    _record_to_chunk,
    _record_to_document,
)
from supportops_api.infrastructure.persistence.models import DocumentChunkRecord, DocumentRecord


def create_indexed_document() -> Document:
    document = Document.create(
        name="Refund Policy",
        document_type=DocumentType.INTERNAL_POLICY,
        product_area=ProductArea.BILLING,
        source_file_name="refund-policy.md",
        content_type="text/markdown",
        size_bytes=1024,
        tags=("refund", "enterprise"),
    )
    document.start_processing()
    document.mark_indexed(chunk_count=2)
    return document


def test_document_record_roundtrip_preserves_domain_values() -> None:
    document = create_indexed_document()

    record = _document_to_record(document)
    mapped_document = _record_to_document(record)

    assert mapped_document.id == document.id
    assert mapped_document.name == "Refund Policy"
    assert mapped_document.document_type == DocumentType.INTERNAL_POLICY
    assert mapped_document.product_area == ProductArea.BILLING
    assert mapped_document.status == DocumentStatus.INDEXED
    assert mapped_document.tags == ("refund", "enterprise")
    assert mapped_document.chunk_count == 2
    assert mapped_document.last_processed_at == document.last_processed_at


def test_chunk_record_roundtrip_preserves_domain_values() -> None:
    chunk = DocumentChunk(
        document_id=uuid4(),
        chunk_index=1,
        content="Enterprise refunds require approval.",
        metadata={"section": "Refund policy"},
    )

    record = _chunk_to_record(chunk)
    mapped_chunk = _record_to_chunk(record)

    assert mapped_chunk.id == chunk.id
    assert mapped_chunk.document_id == chunk.document_id
    assert mapped_chunk.chunk_index == 1
    assert mapped_chunk.content == "Enterprise refunds require approval."
    assert mapped_chunk.metadata == {"section": "Refund policy"}


@pytest.mark.asyncio
async def test_replace_chunks_rejects_chunks_from_another_document() -> None:
    repository = PostgresDocumentRepository(session=None)  # type: ignore[arg-type]
    document_id = uuid4()
    chunks = [DocumentChunk(document_id=uuid4(), chunk_index=0, content="Wrong document")]

    with pytest.raises(ValueError, match="belong to the document"):
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
        DocumentChunk(document_id=document.id, chunk_index=0, content="First chunk"),
        DocumentChunk(document_id=document.id, chunk_index=1, content="Second chunk"),
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
