from __future__ import annotations

from openai import AsyncOpenAI

from supportops_api.application.documents import EmbeddingGenerator, GeneratedEmbedding


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    def __init__(
        self,
        *,
        model: str = "text-embedding-3-small",
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._model = model
        self._client = client or AsyncOpenAI()

    async def generate(self, text: str) -> GeneratedEmbedding:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Text is required to generate an embedding")

        response = await self._client.embeddings.create(
            model=self._model,
            input=normalized_text,
        )
        values = tuple(float(value) for value in response.data[0].embedding)

        return GeneratedEmbedding(values=values, model=self._model, provider="openai")
