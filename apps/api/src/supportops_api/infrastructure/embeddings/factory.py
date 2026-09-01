from __future__ import annotations

import os
from typing import Any

from supportops_api.application.documents import EmbeddingGenerator
from supportops_api.infrastructure.embeddings.deterministic_embedding_generator import (
    DeterministicEmbeddingGenerator,
)
from supportops_api.infrastructure.embeddings.openai_embedding_generator import (
    OpenAIEmbeddingGenerator,
)

DEFAULT_EMBEDDING_PROVIDER = "deterministic"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


def create_embedding_generator(
    provider: str = DEFAULT_EMBEDDING_PROVIDER,
    *,
    openai_model: str = DEFAULT_OPENAI_EMBEDDING_MODEL,
    openai_client: Any | None = None,
) -> EmbeddingGenerator:
    normalized_provider = provider.strip().lower()

    if normalized_provider == "deterministic":
        return DeterministicEmbeddingGenerator()

    if normalized_provider == "openai":
        return OpenAIEmbeddingGenerator(model=openai_model, client=openai_client)

    raise ValueError(f"Unsupported embedding provider: {provider}")


def get_embedding_generator_from_env() -> EmbeddingGenerator:
    return create_embedding_generator(
        os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER),
        openai_model=os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL),
    )
