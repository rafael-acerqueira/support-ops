from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.response_suggestions import (
    KnowledgeChunkCandidate,
    KnowledgeSourceRepository,
)
from supportops_api.domain.documents import DocumentStatus
from supportops_api.infrastructure.persistence.models import DocumentChunkRecord, DocumentRecord


class PostgresDocumentChunkRepository(KnowledgeSourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_indexed_chunks(self, *, limit: int = 50) -> list[KnowledgeChunkCandidate]:
        result = await self._session.execute(
            select(DocumentRecord, DocumentChunkRecord)
            .join(DocumentChunkRecord, DocumentChunkRecord.document_id == DocumentRecord.id)
            .where(
                DocumentRecord.is_active.is_(True),
                DocumentRecord.status == DocumentStatus.INDEXED.value,
            )
            .order_by(DocumentRecord.updated_at.desc(), DocumentChunkRecord.chunk_index.asc())
            .limit(limit)
        )

        return [_record_to_candidate(document, chunk) for document, chunk in result.all()]


def _record_to_candidate(
    document: DocumentRecord, chunk: DocumentChunkRecord
) -> KnowledgeChunkCandidate:
    return KnowledgeChunkCandidate(
        document_id=document.id,
        document_name=document.name,
        document_type=document.document_type,
        product_area=document.product_area,
        tags=tuple(document.tags or []),
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
    )
