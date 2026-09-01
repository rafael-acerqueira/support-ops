from types import SimpleNamespace

from openai import APIConnectionError
import pytest

from supportops_api.application.documents import EmbeddingProviderError
from supportops_api.infrastructure.embeddings import OpenAIEmbeddingGenerator


class FakeEmbeddingsClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []

    async def create(self, *, model: str, input: str) -> SimpleNamespace:
        self.requests.append({"model": model, "input": input})
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1, -0.2, 0.3],
                )
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsClient()


class FailingEmbeddingsClient:
    async def create(self, *, model: str, input: str) -> SimpleNamespace:
        raise APIConnectionError(request=None)


class FailingOpenAIClient:
    embeddings = FailingEmbeddingsClient()


@pytest.mark.asyncio
async def test_openai_embedding_generator_returns_embedding() -> None:
    client = FakeOpenAIClient()
    generator = OpenAIEmbeddingGenerator(model="text-embedding-3-small", client=client)

    embedding = await generator.generate("  Refund   policy  ")

    assert embedding.model == "text-embedding-3-small"
    assert embedding.provider == "openai"
    assert embedding.values == (0.1, -0.2, 0.3)
    assert embedding.dimensions == 3
    assert client.embeddings.requests == [
        {"model": "text-embedding-3-small", "input": "Refund policy"}
    ]


@pytest.mark.asyncio
async def test_openai_embedding_generator_requires_text() -> None:
    with pytest.raises(ValueError, match="Text is required"):
        await OpenAIEmbeddingGenerator(client=FakeOpenAIClient()).generate("   ")


@pytest.mark.asyncio
async def test_openai_embedding_generator_wraps_provider_errors() -> None:
    with pytest.raises(EmbeddingProviderError, match="connection failed"):
        await OpenAIEmbeddingGenerator(client=FailingOpenAIClient()).generate("Refund policy")
