import pytest

from supportops_api.infrastructure.embeddings import DeterministicEmbeddingGenerator


@pytest.mark.asyncio
async def test_deterministic_embedding_generator_returns_expected_dimensions() -> None:
    embedding = await DeterministicEmbeddingGenerator(dimensions=8).generate("Refund policy")

    assert embedding.model == "supportops-deterministic-v1"
    assert embedding.provider == "deterministic"
    assert embedding.dimensions == 8
    assert len(embedding.values) == 8
    assert all(-1 <= value <= 1 for value in embedding.values)


@pytest.mark.asyncio
async def test_deterministic_embedding_generator_is_repeatable() -> None:
    generator = DeterministicEmbeddingGenerator(dimensions=8)

    first = await generator.generate("Duplicate invoice charge")
    second = await generator.generate("Duplicate invoice charge")
    different = await generator.generate("Security escalation")

    assert first == second
    assert first != different


@pytest.mark.asyncio
async def test_deterministic_embedding_generator_requires_text() -> None:
    with pytest.raises(ValueError, match="Text is required"):
        await DeterministicEmbeddingGenerator(dimensions=8).generate("   ")


def test_deterministic_embedding_generator_requires_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        DeterministicEmbeddingGenerator(dimensions=0)
