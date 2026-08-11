from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from supportops_api.domain.documents import Document, DocumentStatus, DocumentType, ProductArea


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
    content_type: str
    size_bytes: int
    chunk_count: int
    failure_reason: str | None
    last_processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> DocumentResponse:
        return cls(
            id=document.id,
            name=document.name,
            document_type=document.document_type,
            product_area=document.product_area,
            version=document.version,
            status=document.status,
            is_active=document.is_active,
            tags=list(document.tags),
            source_file_name=document.source_file_name,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            chunk_count=document.chunk_count,
            failure_reason=document.failure_reason,
            last_processed_at=document.last_processed_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
