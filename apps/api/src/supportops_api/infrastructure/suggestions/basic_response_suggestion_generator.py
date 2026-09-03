from __future__ import annotations

from supportops_api.application.response_suggestions import (
    GeneratedSuggestedResponse,
    ResponseSuggestionGenerator,
    RetrievedKnowledgeSource,
    TicketKnowledgeRetriever,
    confidence_level_for_score,
    confidence_reason_from_sources,
    confidence_score_from_sources,
)
from supportops_api.domain.tickets import Ticket


class BasicResponseSuggestionGenerator(ResponseSuggestionGenerator):
    def __init__(
        self,
        knowledge_retriever: TicketKnowledgeRetriever | None = None,
        *,
        source_limit: int = 3,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._source_limit = source_limit

    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        knowledge_sources = (
            await self._knowledge_retriever.retrieve(ticket, limit=self._source_limit)
            if self._knowledge_retriever
            else []
        )

        content = _build_content(ticket, knowledge_sources)
        sources = [_source_to_response(source) for source in knowledge_sources]
        confidence_score = confidence_score_from_sources(knowledge_sources)
        return GeneratedSuggestedResponse(
            content=content,
            sources=sources,
            confidence_score=confidence_score,
            confidence_level=confidence_level_for_score(confidence_score),
            confidence_reason=confidence_reason_from_sources(knowledge_sources),
        )


def _build_content(ticket: Ticket, sources: list[RetrievedKnowledgeSource]) -> str:
    context_note = (
        "I reviewed the indexed internal sources most relevant to this request."
        if sources
        else "I could not find indexed internal sources for this request, so this draft needs careful human review before sending."
    )

    return (
        f"Hi {ticket.customer_name},\n\n"
        f"Thanks for reaching out about {ticket.subject.lower()}. "
        f"{context_note}\n\n"
        "Next steps:\n"
        "1. Validate the account and impacted product area.\n"
        "2. Confirm the applicable policy details before taking action.\n"
        "3. Reply with the approved resolution or escalation path.\n\n"
        "Best,\nSupportOps"
    )


def _source_to_response(source: RetrievedKnowledgeSource) -> dict[str, object]:
    return {
        "document_id": str(source.document_id),
        "chunk_id": str(source.chunk_id),
        "chunk_index": source.chunk_index,
        "document_name": source.document_name,
        "document_type": source.document_type,
        "relevance_score": source.relevance_score,
        "excerpt": _excerpt(source.content),
    }


def _excerpt(content: str, *, max_length: int = 280) -> str:
    clean_content = " ".join(content.split())
    if len(clean_content) <= max_length:
        return clean_content

    return f"{clean_content[: max_length - 3].rstrip()}..."
