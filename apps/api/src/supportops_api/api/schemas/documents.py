from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from supportops_api.domain.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    ProductArea,
)


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    document_type: DocumentType
    product_area: ProductArea
    source_file_name: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    id: UUID
    name: str
    document_type: DocumentType
    product_area: ProductArea
    version: str
    status: DocumentStatus
    is_active: bool
    tags: list[str]
    source_file_name: str
    storage_key: str | None
    content_type: str
    size_bytes: int
    chunk_count: int
    failure_reason: str | None
    last_processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls,
        document: Document,
        processing_version: DocumentVersion | None = None,
    ) -> DocumentResponse:
        version = processing_version
        return cls(
            id=document.id,
            name=document.name,
            document_type=document.document_type,
            product_area=document.product_area,
            version=version.version if version else document.version,
            status=version.status if version else document.status,
            is_active=document.is_active,
            tags=list(document.tags),
            source_file_name=version.source_file_name if version else document.source_file_name,
            storage_key=version.storage_key if version else document.storage_key,
            content_type=version.content_type if version else document.content_type,
            size_bytes=version.size_bytes if version else document.size_bytes,
            chunk_count=version.chunk_count if version else document.chunk_count,
            failure_reason=version.failure_reason if version else document.failure_reason,
            last_processed_at=version.last_processed_at if version else document.last_processed_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_version_id: UUID | None
    chunk_index: int
    content: str
    metadata: dict
    has_embedding: bool
    embedding_provider: str | None
    embedding_model: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, chunk: DocumentChunk) -> DocumentChunkResponse:
        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            metadata=chunk.metadata,
            has_embedding=chunk.embedding is not None,
            embedding_provider=chunk.embedding_provider,
            embedding_model=chunk.embedding_model,
            created_at=chunk.created_at,
        )


class DocumentVersionResponse(BaseModel):
    id: UUID
    document_id: UUID
    version: str
    status: DocumentStatus
    is_active: bool
    source_file_name: str
    storage_key: str
    content_type: str
    size_bytes: int
    chunk_count: int
    failure_reason: str | None
    activated_at: datetime | None
    last_processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, version: DocumentVersion) -> DocumentVersionResponse:
        return cls(
            id=version.id,
            document_id=version.document_id,
            version=version.version,
            status=version.status,
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


class DocumentProcessingResponse(BaseModel):
    document_id: UUID
    task_id: str
    status: str
