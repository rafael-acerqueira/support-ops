from __future__ import annotations

import re

from supportops_api.application.response_suggestions import (
    KnowledgeChunkCandidate,
    KnowledgeSourceRepository,
    RetrievedKnowledgeSource,
    TicketKnowledgeRetriever,
)
from supportops_api.domain.tickets import Ticket


class BasicTicketKnowledgeRetriever(TicketKnowledgeRetriever):
    def __init__(
        self,
        repository: KnowledgeSourceRepository,
        *,
        candidate_limit: int = 50,
    ) -> None:
        self._repository = repository
        self._candidate_limit = candidate_limit

    async def retrieve(self, ticket: Ticket, *, limit: int = 3) -> list[RetrievedKnowledgeSource]:
        candidates = await self._repository.list_indexed_chunks(limit=self._candidate_limit)
        ranked_sources = [
            RetrievedKnowledgeSource(
                document_id=candidate.document_id,
                document_name=candidate.document_name,
                document_type=candidate.document_type,
                chunk_id=candidate.chunk_id,
                chunk_index=candidate.chunk_index,
                content=candidate.content,
                relevance_score=_score_candidate(ticket, candidate),
            )
            for candidate in candidates
        ]
        ranked_sources.sort(key=lambda source: source.relevance_score, reverse=True)

        return [source for source in ranked_sources if source.relevance_score > 0][:limit]


def _score_candidate(ticket: Ticket, candidate: KnowledgeChunkCandidate) -> float:
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
                candidate.document_name,
                candidate.document_type,
                candidate.product_area,
                " ".join(candidate.tags),
                candidate.content,
            ]
        )
    )

    if not ticket_terms or not source_terms:
        return 0

    overlap_score = len(ticket_terms & source_terms) / len(ticket_terms)
    area_score = 0.35 if candidate.product_area == ticket.product_area.value else 0
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
