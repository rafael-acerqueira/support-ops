from __future__ import annotations

from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from supportops_api.application.response_suggestions import (
    GeneratedSuggestedResponse,
    ResponseGenerationProviderError,
    ResponseSuggestionGenerator,
    RetrievedKnowledgeSource,
    TicketKnowledgeRetriever,
    confidence_level_for_score,
    confidence_reason_from_sources,
    confidence_score_from_sources,
)
from supportops_api.domain.tickets import Ticket
from supportops_api.infrastructure.suggestions.basic_response_suggestion_generator import (
    _source_to_response,
)


class OpenAIResponseSuggestionGenerator(ResponseSuggestionGenerator):
    def __init__(
        self,
        knowledge_retriever: TicketKnowledgeRetriever,
        *,
        model: str = "gpt-4o-mini",
        source_limit: int = 3,
        client: Any | None = None,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._model = model
        self._source_limit = source_limit
        self._client = client

    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        knowledge_sources = await self._knowledge_retriever.retrieve(
            ticket, limit=self._source_limit
        )
        response = await self._create_response(ticket, knowledge_sources)
        content = response.output_text.strip()

        if not content:
            raise ResponseGenerationProviderError(
                "OpenAI response generation returned empty content."
            )

        confidence_score = confidence_score_from_sources(knowledge_sources)
        return GeneratedSuggestedResponse(
            content=content,
            sources=[_source_to_response(source) for source in knowledge_sources],
            confidence_score=confidence_score,
            confidence_level=confidence_level_for_score(confidence_score),
            confidence_reason=confidence_reason_from_sources(knowledge_sources),
        )

    async def _create_response(
        self, ticket: Ticket, sources: list[RetrievedKnowledgeSource]
    ) -> Any:
        try:
            return await self._get_client().responses.create(
                model=self._model,
                instructions=_build_instructions(),
                input=_build_input(ticket, sources),
                temperature=0.2,
            )
        except AuthenticationError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation authentication failed. Check OPENAI_API_KEY."
            ) from exc
        except PermissionDeniedError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation was denied. Check project permissions."
            ) from exc
        except RateLimitError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation rate limit or quota was reached. Try again later or check billing."
            ) from exc
        except APITimeoutError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation timed out. Try generating the suggestion again."
            ) from exc
        except APIConnectionError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation connection failed. Check network access and try again."
            ) from exc
        except BadRequestError as exc:
            raise ResponseGenerationProviderError(
                f"OpenAI response generation request was invalid for model {self._model}."
            ) from exc
        except APIError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation service returned an error. Try generating the suggestion again."
            ) from exc
        except OpenAIError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation failed. Check provider configuration and try again."
            ) from exc

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            self._client = AsyncOpenAI()
        except OpenAIError as exc:
            raise ResponseGenerationProviderError(
                "OpenAI response generation is not configured. Set OPENAI_API_KEY or use "
                "RESPONSE_GENERATOR_PROVIDER=deterministic."
            ) from exc

        return self._client


def _build_instructions() -> str:
    return (
        "# Role\n"
        "You are SupportOps, a customer support operations assistant for B2B SaaS teams.\n\n"
        "# Objective\n"
        "Draft a concise customer-facing support reply for a human agent to review.\n\n"
        "# Hard constraints\n"
        "- Use only the provided ticket and retrieved internal knowledge sources.\n"
        "- Do not invent policies, refunds, credits, SLAs, timelines, security guarantees, "
        "or account actions.\n"
        "- Do not expose internal document IDs, chunk IDs, retrieval scores, or implementation details.\n"
        "- If the sources are insufficient, avoid making a final commitment and include an "
        "Internal review note with what the agent should verify.\n\n"
        "# Tone\n"
        "Be professional, clear, empathetic, and direct. Avoid over-apologizing.\n\n"
        "# Output format\n"
        "Return only the suggested response text. Start with a greeting, explain the next step or "
        "policy-aware guidance, and close with SupportOps."
    )


def _build_input(ticket: Ticket, sources: list[RetrievedKnowledgeSource]) -> str:
    sources_text = "\n\n".join(
        (
            f"Source {index + 1}: {source.document_name} "
            f"({source.document_type}, chunk {source.chunk_index + 1}, "
            f"relevance {source.relevance_score})\n{source.content}"
        )
        for index, source in enumerate(sources)
    )
    if not sources_text:
        sources_text = "No indexed internal knowledge sources were retrieved."

    return (
        "# Ticket\n"
        f"- Customer: {ticket.customer_name}\n"
        f"- Plan: {ticket.customer_tier}\n"
        f"- Subject: {ticket.subject}\n"
        f"- Product area: {ticket.product_area.value}\n"
        f"- Priority: {ticket.priority.value}\n"
        f"- Status: {ticket.status.value}\n"
        f"- Description: {ticket.description}\n\n"
        "# Retrieved internal knowledge sources\n"
        f"{sources_text}\n\n"
        "# Task\n"
        "Write the suggested response in English. Ground every concrete policy statement in the "
        "retrieved sources. If the retrieved sources do not support a concrete answer, produce a "
        "careful draft that asks for confirmation or includes an Internal review note."
    )
