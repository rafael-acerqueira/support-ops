from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import DocumentRepository, DocumentVersionRepository
from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)
from supportops_api.infrastructure.persistence.models import (
    DocumentChunkRecord,
    DocumentRecord,
    DocumentVersionRecord,
)


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

    async def list_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunkRecord)
            .outerjoin(
                DocumentVersionRecord,
                DocumentChunkRecord.document_version_id == DocumentVersionRecord.id,
            )
            .where(DocumentChunkRecord.document_id == document_id)
            .where(_active_or_legacy_chunk_version_filter())
            .order_by(DocumentChunkRecord.chunk_index.asc())
        )
        return [_record_to_chunk(record) for record in result.scalars()]

    async def list_chunks_for_version(
        self, document_id: UUID, document_version_id: UUID
    ) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunkRecord)
            .where(DocumentChunkRecord.document_id == document_id)
            .where(DocumentChunkRecord.document_version_id == document_version_id)
            .order_by(DocumentChunkRecord.chunk_index.asc())
        )
        return [_record_to_chunk(record) for record in result.scalars()]

    async def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        if any(chunk.document_id != document_id for chunk in chunks):
            raise ValueError("All chunks must belong to the document being replaced")

        replacement_version_id = _chunk_replacement_version_id(chunks)

        delete_statement = delete(DocumentChunkRecord).where(
            DocumentChunkRecord.document_id == document_id
        )
        if replacement_version_id:
            delete_statement = delete_statement.where(
                DocumentChunkRecord.document_version_id == replacement_version_id
            )

        await self._session.execute(delete_statement)
        self._session.add_all(_chunk_to_record(chunk) for chunk in chunks)
        await self._session.flush()


class PostgresDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, version: DocumentVersion) -> None:
        self._session.add(_version_to_record(version))
        await self._session.flush()

    async def save(self, version: DocumentVersion) -> None:
        record = await self._session.get(DocumentVersionRecord, version.id)
        if record is None:
            self._session.add(_version_to_record(version))
        else:
            _update_version_record(record, version)

        await self._session.flush()

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        record = await self._session.get(DocumentVersionRecord, version_id)
        if record is None:
            return None

        return _record_to_version(record)

    async def list_for_document(self, document_id: UUID) -> list[DocumentVersion]:
        result = await self._session.execute(
            select(DocumentVersionRecord)
            .where(DocumentVersionRecord.document_id == document_id)
            .order_by(DocumentVersionRecord.created_at.desc())
        )
        return [_record_to_version(record) for record in result.scalars()]

    async def get_for_document_snapshot(
        self, document_id: UUID, version: str, storage_key: str
    ) -> DocumentVersion | None:
        result = await self._session.execute(
            select(DocumentVersionRecord)
            .where(DocumentVersionRecord.document_id == document_id)
            .where(DocumentVersionRecord.version == version)
            .where(DocumentVersionRecord.storage_key == storage_key)
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        return _record_to_version(record)

    async def deactivate_all_for_document(self, document_id: UUID) -> None:
        await self._session.execute(
            update(DocumentVersionRecord)
            .where(DocumentVersionRecord.document_id == document_id)
            .values(is_active=False)
        )
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
        current_version_id=document.current_version_id,
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
    record.current_version_id = document.current_version_id
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
        current_version_id=record.current_version_id,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        chunk_count=record.chunk_count,
        failure_reason=record.failure_reason,
        last_processed_at=record.last_processed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _version_to_record(version: DocumentVersion) -> DocumentVersionRecord:
    return DocumentVersionRecord(
        id=version.id,
        document_id=version.document_id,
        version=version.version,
        status=version.status.value,
        is_active=version.is_active,
        source_file_name=version.source_file_name,
        storage_key=version.storage_key,
        content_type=version.content_type,
        size_bytes=version.size_bytes,
        chunk_count=version.chunk_count,
        failure_reason=version.failure_reason,
        activated_at=version.activated_at,
        last_processed_at=version.last_processed_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _update_version_record(record: DocumentVersionRecord, version: DocumentVersion) -> None:
    record.document_id = version.document_id
    record.version = version.version
    record.status = version.status.value
    record.is_active = version.is_active
    record.source_file_name = version.source_file_name
    record.storage_key = version.storage_key
    record.content_type = version.content_type
    record.size_bytes = version.size_bytes
    record.chunk_count = version.chunk_count
    record.failure_reason = version.failure_reason
    record.activated_at = version.activated_at
    record.last_processed_at = version.last_processed_at
    record.created_at = version.created_at
    record.updated_at = version.updated_at


def _record_to_version(record: DocumentVersionRecord) -> DocumentVersion:
    return DocumentVersion(
        id=record.id,
        document_id=record.document_id,
        version=record.version,
        status=DocumentStatus(record.status),
        is_active=record.is_active,
        source_file_name=record.source_file_name,
        storage_key=record.storage_key,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        chunk_count=record.chunk_count,
        failure_reason=record.failure_reason,
        activated_at=record.activated_at,
        last_processed_at=record.last_processed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _chunk_to_record(chunk: DocumentChunk) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=chunk.id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        chunk_metadata=chunk.metadata,
        embedding=list(chunk.embedding) if chunk.embedding is not None else None,
        embedding_provider=chunk.embedding_provider,
        embedding_model=chunk.embedding_model,
        created_at=chunk.created_at,
    )


def _record_to_chunk(record: DocumentChunkRecord) -> DocumentChunk:
    return DocumentChunk(
        id=record.id,
        document_id=record.document_id,
        document_version_id=record.document_version_id,
        chunk_index=record.chunk_index,
        content=record.content,
        metadata=record.chunk_metadata,
        embedding=_embedding_to_tuple(record.embedding),
        embedding_provider=record.embedding_provider,
        embedding_model=record.embedding_model,
        created_at=record.created_at,
    )


def _chunk_replacement_version_id(chunks: list[DocumentChunk]) -> UUID | None:
    version_ids = {chunk.document_version_id for chunk in chunks if chunk.document_version_id}
    if len(version_ids) > 1:
        raise ValueError("All chunks must belong to the same document version")

    return next(iter(version_ids), None)


def _active_or_legacy_chunk_version_filter():
    return or_(
        DocumentChunkRecord.document_version_id.is_(None),
        and_(
            DocumentVersionRecord.is_active.is_(True),
            DocumentVersionRecord.status == DocumentStatus.INDEXED.value,
        ),
    )


def _embedding_to_tuple(value: Sequence[float] | str | None) -> tuple[float, ...] | None:
    if value is None:
        return None

    if isinstance(value, str):
        return tuple(float(item) for item in value.strip("[]").split(",") if item)

    return tuple(float(item) for item in value)
