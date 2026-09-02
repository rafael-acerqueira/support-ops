from __future__ import annotations

import os
from typing import Any

from supportops_api.application.response_suggestions import (
    ResponseSuggestionGenerator,
    TicketKnowledgeRetriever,
)
from supportops_api.infrastructure.suggestions.basic_response_suggestion_generator import (
    BasicResponseSuggestionGenerator,
)
from supportops_api.infrastructure.suggestions.openai_response_suggestion_generator import (
    OpenAIResponseSuggestionGenerator,
)

DEFAULT_RESPONSE_GENERATOR_PROVIDER = "deterministic"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def create_response_suggestion_generator(
    provider: str = DEFAULT_RESPONSE_GENERATOR_PROVIDER,
    *,
    knowledge_retriever: TicketKnowledgeRetriever,
    openai_model: str = DEFAULT_OPENAI_MODEL,
    openai_client: Any | None = None,
) -> ResponseSuggestionGenerator:
    normalized_provider = provider.strip().lower()
    normalized_openai_model = openai_model.strip()

    if normalized_provider == "deterministic":
        return BasicResponseSuggestionGenerator(knowledge_retriever)

    if normalized_provider == "openai":
        if not normalized_openai_model:
            raise ValueError("OPENAI_MODEL is required when RESPONSE_GENERATOR_PROVIDER=openai")

        return OpenAIResponseSuggestionGenerator(
            knowledge_retriever,
            model=normalized_openai_model,
            client=openai_client,
        )

    raise ValueError(f"Unsupported response generator provider: {provider}")


def get_response_suggestion_generator_from_env(
    knowledge_retriever: TicketKnowledgeRetriever,
) -> ResponseSuggestionGenerator:
    return create_response_suggestion_generator(
        os.getenv("RESPONSE_GENERATOR_PROVIDER", DEFAULT_RESPONSE_GENERATOR_PROVIDER),
        knowledge_retriever=knowledge_retriever,
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    )
