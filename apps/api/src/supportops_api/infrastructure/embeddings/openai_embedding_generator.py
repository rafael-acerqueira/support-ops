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

from supportops_api.application.documents import (
    EmbeddingGenerator,
    EmbeddingProviderError,
    GeneratedEmbedding,
)


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    def __init__(
        self,
        *,
        model: str = "text-embedding-3-small",
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._client = client

    async def generate(self, text: str) -> GeneratedEmbedding:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Text is required to generate an embedding")

        try:
            response = await self._get_client().embeddings.create(
                model=self._model,
                input=normalized_text,
            )
        except AuthenticationError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings authentication failed. Check OPENAI_API_KEY."
            ) from exc
        except PermissionDeniedError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings request was denied. Check project permissions."
            ) from exc
        except RateLimitError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings rate limit or quota was reached. Try again later or check billing."
            ) from exc
        except APITimeoutError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings request timed out. Try reprocessing the document."
            ) from exc
        except APIConnectionError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings connection failed. Check network access and try again."
            ) from exc
        except BadRequestError as exc:
            raise EmbeddingProviderError(
                f"OpenAI embeddings request was invalid for model {self._model}."
            ) from exc
        except APIError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings service returned an error. Try reprocessing the document."
            ) from exc
        except OpenAIError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings failed. Check provider configuration and try again."
            ) from exc

        values = tuple(float(value) for value in response.data[0].embedding)

        return GeneratedEmbedding(values=values, model=self._model, provider="openai")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            self._client = AsyncOpenAI()
        except OpenAIError as exc:
            raise EmbeddingProviderError(
                "OpenAI embeddings are not configured. Set OPENAI_API_KEY or use "
                "EMBEDDING_PROVIDER=deterministic."
            ) from exc

        return self._client
