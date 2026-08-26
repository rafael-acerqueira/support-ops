from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.response_suggestions import RetrievedKnowledgeSource
from supportops_api.domain.documents import DocumentStatus
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.persistence.models import DocumentChunkRecord, DocumentRecord


class PostgresTicketKnowledgeRetriever:
    def __init__(self, session: AsyncSession, *, candidate_limit: int = 50) -> None:
        self._session = session
        self._candidate_limit = candidate_limit

    async def retrieve(self, ticket: Ticket, *, limit: int = 3) -> list[RetrievedKnowledgeSource]:
        result = await self._session.execute(
            select(DocumentRecord, DocumentChunkRecord)
            .join(DocumentChunkRecord, DocumentChunkRecord.document_id == DocumentRecord.id)
            .where(
                DocumentRecord.is_active.is_(True),
                DocumentRecord.status == DocumentStatus.INDEXED.value,
            )
            .order_by(DocumentRecord.updated_at.desc(), DocumentChunkRecord.chunk_index.asc())
            .limit(self._candidate_limit)
        )

        ranked_sources = [
            RetrievedKnowledgeSource(
                document_id=document.id,
                document_name=document.name,
                document_type=document.document_type,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                relevance_score=_score_source(ticket, document, chunk),
            )
            for document, chunk in result.all()
        ]
        ranked_sources.sort(key=lambda source: source.relevance_score, reverse=True)

        return [source for source in ranked_sources if source.relevance_score > 0][:limit]


def _score_source(ticket: Ticket, document: DocumentRecord, chunk: DocumentChunkRecord) -> float:
    ticket_terms = _tokenize(
        " ".join(
            [
                ticket.external_id,
                ticket.customer_name,
                ticket.customer_tier,
                ticket.subject,
                ticket.description,
                ticket.product_area.value,
            ]
        )
    )
    source_terms = _tokenize(
        " ".join(
            [
                document.name,
                document.document_type,
                document.product_area,
                " ".join(document.tags or []),
                chunk.content,
            ]
        )
    )

    if not ticket_terms or not source_terms:
        return 0

    overlap_score = len(ticket_terms & source_terms) / len(ticket_terms)
    area_score = 0.35 if document.product_area == ticket.product_area.value else 0
    tier_score = 0.15 if ticket.customer_tier in source_terms else 0

    return round(min(overlap_score + area_score + tier_score, 0.99), 2)


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in _STOP_WORDS
    }


_STOP_WORDS = {
    "and",
    "for",
    "the",
    "this",
    "that",
    "with",
    "from",
    "about",
    "into",
    "being",
    "cannot",
}
