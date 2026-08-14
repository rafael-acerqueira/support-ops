from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import DocumentRepository
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    ProductArea,
)
from supportops_api.infrastructure.persistence.models import DocumentChunkRecord, DocumentRecord


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(_document_to_record(document))
        await self._session.flush()

    async def save(self, document: Document) -> None:
        record = await self._session.get(DocumentRecord, document.id)
        if record is None:
            self._session.add(_document_to_record(document))
        else:
            _update_document_record(record, document)

        await self._session.flush()

    async def get(self, document_id: UUID) -> Document | None:
        record = await self._session.get(DocumentRecord, document_id)
        if record is None:
            return None

        return _record_to_document(record)

    async def list_all(self) -> list[Document]:
        result = await self._session.execute(
            select(DocumentRecord).order_by(DocumentRecord.created_at.desc())
        )
        return [_record_to_document(record) for record in result.scalars()]

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        if any(chunk.document_id != document_id for chunk in chunks):
            raise ValueError("All chunks must belong to the document being replaced")

        await self._session.execute(
            delete(DocumentChunkRecord).where(DocumentChunkRecord.document_id == document_id)
        )
        self._session.add_all(_chunk_to_record(chunk) for chunk in chunks)
        await self._session.flush()


def _document_to_record(document: Document) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        name=document.name,
        document_type=document.document_type.value,
        product_area=document.product_area.value,
        version=document.version,
        status=document.status.value,
        is_active=document.is_active,
        tags=list(document.tags),
        source_file_name=document.source_file_name,
        storage_key=document.storage_key,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        chunk_count=document.chunk_count,
        failure_reason=document.failure_reason,
        last_processed_at=document.last_processed_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _update_document_record(record: DocumentRecord, document: Document) -> None:
    record.name = document.name
    record.document_type = document.document_type.value
    record.product_area = document.product_area.value
    record.version = document.version
    record.status = document.status.value
    record.is_active = document.is_active
    record.tags = list(document.tags)
    record.source_file_name = document.source_file_name
    record.storage_key = document.storage_key
    record.content_type = document.content_type
    record.size_bytes = document.size_bytes
    record.chunk_count = document.chunk_count
    record.failure_reason = document.failure_reason
    record.last_processed_at = document.last_processed_at
    record.created_at = document.created_at
    record.updated_at = document.updated_at


def _record_to_document(record: DocumentRecord) -> Document:
    return Document(
        id=record.id,
        name=record.name,
        document_type=DocumentType(record.document_type),
        product_area=ProductArea(record.product_area),
        version=record.version,
        status=DocumentStatus(record.status),
        is_active=record.is_active,
        tags=tuple(record.tags),
        source_file_name=record.source_file_name,
        storage_key=record.storage_key,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        chunk_count=record.chunk_count,
        failure_reason=record.failure_reason,
        last_processed_at=record.last_processed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _chunk_to_record(chunk: DocumentChunk) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        chunk_metadata=chunk.metadata,
        created_at=chunk.created_at,
    )


def _record_to_chunk(record: DocumentChunkRecord) -> DocumentChunk:
    return DocumentChunk(
        id=record.id,
        document_id=record.document_id,
        chunk_index=record.chunk_index,
        content=record.content,
        metadata=record.chunk_metadata,
        created_at=record.created_at,
    )
