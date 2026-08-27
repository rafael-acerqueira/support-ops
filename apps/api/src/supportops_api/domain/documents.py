from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(StrEnum):
    INTERNAL_POLICY = "internal_policy"
    SLA_POLICY = "sla_policy"
    SECURITY_POLICY = "security_policy"
    INCIDENT_POLICY = "incident_policy"
    PLAYBOOK = "playbook"
    FAQ = "faq"
    TECHNICAL_DOCUMENTATION = "technical_documentation"


class ProductArea(StrEnum):
    BILLING = "billing"
    SECURITY = "security"
    SUPPORT = "support"
    API = "api"
    PRODUCT = "product"
    LEGAL = "legal"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
    normalized = []
    seen = set()

    for tag in tags:
        value = tag.strip().lower()
        if not value or value in seen:
            continue

        normalized.append(value)
        seen.add(value)

    return tuple(normalized)


@dataclass
class Document:
    name: str
    document_type: DocumentType
    product_area: ProductArea
    source_file_name: str
    content_type: str
    size_bytes: int
    tags: tuple[str, ...] = field(default_factory=tuple)
    storage_key: str | None = None
    id: UUID = field(default_factory=uuid4)
    version: str = "v1"
    status: DocumentStatus = DocumentStatus.UPLOADED
    is_active: bool = True
    chunk_count: int = 0
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    last_processed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.source_file_name = self.source_file_name.strip()
        self.content_type = self.content_type.strip()
        self.tags = _normalize_tags(self.tags)
        self.storage_key = self.storage_key.strip() if self.storage_key else None

        if not self.name:
            raise ValueError("Document name is required")
        if not self.source_file_name:
            raise ValueError("Source file name is required")
        if not self.content_type:
            raise ValueError("Content type is required")
        if self.storage_key == "":
            raise ValueError("Storage key cannot be blank")
        if self.size_bytes <= 0:
            raise ValueError("Document size must be greater than zero")
        if self.chunk_count < 0:
            raise ValueError("Chunk count cannot be negative")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        document_type: DocumentType,
        product_area: ProductArea,
        source_file_name: str,
        content_type: str,
        size_bytes: int,
        tags: tuple[str, ...] = (),
        storage_key: str | None = None,
    ) -> Document:
        return cls(
            name=name,
            document_type=document_type,
            product_area=product_area,
            source_file_name=source_file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            tags=tags,
            storage_key=storage_key,
        )

    def start_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.failure_reason = None
        self.updated_at = _utcnow()

    def mark_indexed(self, *, chunk_count: int) -> None:
        if chunk_count <= 0:
            raise ValueError("Indexed documents must have at least one chunk")

        now = _utcnow()
        self.status = DocumentStatus.INDEXED
        self.chunk_count = chunk_count
        self.failure_reason = None
        self.last_processed_at = now
        self.updated_at = now

    def mark_failed(self, reason: str) -> None:
        reason = reason.strip()
        if not reason:
            raise ValueError("Failure reason is required")

        self.status = DocumentStatus.FAILED
        self.failure_reason = reason
        self.updated_at = _utcnow()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _utcnow()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utcnow()


@dataclass(frozen=True)
class DocumentChunk:
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: tuple[float, ...] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        content = self.content.strip()
        embedding = tuple(float(value) for value in self.embedding) if self.embedding else None

        if self.chunk_index < 0:
            raise ValueError("Chunk index cannot be negative")
        if not content:
            raise ValueError("Chunk content is required")
        if self.embedding is not None and embedding is None:
            raise ValueError("Chunk embedding cannot be empty")

        object.__setattr__(self, "content", content)
        object.__setattr__(self, "embedding", embedding)
