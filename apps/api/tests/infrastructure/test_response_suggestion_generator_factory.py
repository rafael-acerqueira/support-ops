import pytest

from supportops_api.infrastructure.suggestions import (
    BasicResponseSuggestionGenerator,
    OpenAIResponseSuggestionGenerator,
    create_response_suggestion_generator,
    get_response_suggestion_generator_from_env,
)


class FakeKnowledgeRetriever:
    pass


class FakeOpenAIClient:
    responses = object()


def test_create_response_suggestion_generator_returns_basic_by_default() -> None:
    generator = create_response_suggestion_generator(
        knowledge_retriever=FakeKnowledgeRetriever(),
    )

    assert isinstance(generator, BasicResponseSuggestionGenerator)


def test_create_response_suggestion_generator_returns_openai_provider() -> None:
    generator = create_response_suggestion_generator(
        "openai",
        knowledge_retriever=FakeKnowledgeRetriever(),
        openai_model="gpt-4o-mini",
        openai_client=FakeOpenAIClient(),
    )

    assert isinstance(generator, OpenAIResponseSuggestionGenerator)


def test_create_response_suggestion_generator_rejects_blank_openai_model() -> None:
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        create_response_suggestion_generator(
            "openai",
            knowledge_retriever=FakeKnowledgeRetriever(),
            openai_model="   ",
            openai_client=FakeOpenAIClient(),
        )


def test_create_response_suggestion_generator_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported response generator provider"):
        create_response_suggestion_generator(
            "unknown",
            knowledge_retriever=FakeKnowledgeRetriever(),
        )


def test_get_response_suggestion_generator_from_env_uses_basic_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RESPONSE_GENERATOR_PROVIDER", raising=False)

    generator = get_response_suggestion_generator_from_env(FakeKnowledgeRetriever())

    assert isinstance(generator, BasicResponseSuggestionGenerator)
