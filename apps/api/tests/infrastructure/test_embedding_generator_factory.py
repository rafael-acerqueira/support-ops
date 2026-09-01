import pytest

from supportops_api.infrastructure.embeddings import (
    DeterministicEmbeddingGenerator,
    OpenAIEmbeddingGenerator,
    create_embedding_generator,
    get_embedding_generator_from_env,
)


class FakeOpenAIClient:
    embeddings = object()


def test_create_embedding_generator_returns_deterministic_by_default() -> None:
    generator = create_embedding_generator()

    assert isinstance(generator, DeterministicEmbeddingGenerator)


def test_create_embedding_generator_returns_openai_provider() -> None:
    generator = create_embedding_generator(
        "openai",
        openai_model="text-embedding-3-large",
        openai_client=FakeOpenAIClient(),
    )

    assert isinstance(generator, OpenAIEmbeddingGenerator)


def test_create_embedding_generator_rejects_blank_openai_model() -> None:
    with pytest.raises(ValueError, match="OPENAI_EMBEDDING_MODEL"):
        create_embedding_generator("openai", openai_model="   ", openai_client=FakeOpenAIClient())


def test_create_embedding_generator_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        create_embedding_generator("unknown")


def test_get_embedding_generator_from_env_uses_deterministic_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    generator = get_embedding_generator_from_env()

    assert isinstance(generator, DeterministicEmbeddingGenerator)
