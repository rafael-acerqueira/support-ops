from __future__ import annotations

from sqlalchemy import Float, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from supportops_api.application.response_suggestions import (
    KnowledgeChunkCandidate,
    KnowledgeSourceRepository,
    RetrievedKnowledgeSource,
)
from supportops_api.domain.documents import DocumentStatus
from supportops_api.infrastructure.persistence.models import (
    DocumentChunkRecord,
    DocumentRecord,
    Vector,
)


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

    async def search_similar_chunks(
        self,
        *,
        embedding: tuple[float, ...],
        limit: int = 3,
    ) -> list[RetrievedKnowledgeSource]:
        if limit <= 0:
            return []

        distance = _vector_distance_expression(embedding)

        result = await self._session.execute(
            select(DocumentRecord, DocumentChunkRecord, distance.label("distance"))
            .join(DocumentChunkRecord, DocumentChunkRecord.document_id == DocumentRecord.id)
            .where(
                DocumentRecord.is_active.is_(True),
                DocumentRecord.status == DocumentStatus.INDEXED.value,
                DocumentChunkRecord.embedding.is_not(None),
            )
            .order_by(
                distance.asc(),
                DocumentRecord.updated_at.desc(),
                DocumentChunkRecord.chunk_index.asc(),
            )
            .limit(limit)
        )

        return [
            _record_to_source(document, chunk, distance)
            for document, chunk, distance in result.all()
        ]


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


def _record_to_source(
    document: DocumentRecord,
    chunk: DocumentChunkRecord,
    distance: float,
) -> RetrievedKnowledgeSource:
    return RetrievedKnowledgeSource(
        document_id=document.id,
        document_name=document.name,
        document_type=document.document_type,
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        relevance_score=_distance_to_relevance(distance),
    )


def _distance_to_relevance(distance: float) -> float:
    return round(max(0.0, min(0.99, 1 - float(distance))), 2)


def _vector_distance_expression(embedding: tuple[float, ...]) -> ColumnElement[float]:
    query_vector = literal(embedding, type_=Vector(len(embedding)))
    return DocumentChunkRecord.embedding.op("<=>", return_type=Float())(query_vector)
