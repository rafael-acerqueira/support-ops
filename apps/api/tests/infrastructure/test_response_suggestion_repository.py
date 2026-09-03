from uuid import uuid4

from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
    SuggestedResponseConfidenceLevel,
    SuggestedResponseStatus,
)
from supportops_api.infrastructure.persistence.response_suggestion_repository import (
    _record_to_suggestion,
    _suggestion_to_record,
)


def test_suggestion_record_roundtrip_preserves_domain_values() -> None:
    suggestion = SuggestedResponse.create(
        ticket_id=uuid4(),
        content="Draft reply",
        sources=[{"document_id": str(uuid4()), "label": "Refund policy"}],
        confidence_score=0.76,
        confidence_level=SuggestedResponseConfidenceLevel.HIGH,
        confidence_reason="Best retrieved source matched this ticket with 76% relevance from refund-policy.md.",
    )
    suggestion.approve()

    record = _suggestion_to_record(suggestion)
    mapped_suggestion = _record_to_suggestion(record)

    assert mapped_suggestion.id == suggestion.id
    assert mapped_suggestion.ticket_id == suggestion.ticket_id
    assert mapped_suggestion.content == "Draft reply"
    assert mapped_suggestion.status == SuggestedResponseStatus.APPROVED
    assert mapped_suggestion.sources == suggestion.sources
    assert mapped_suggestion.confidence_score == 0.76
    assert mapped_suggestion.confidence_level == SuggestedResponseConfidenceLevel.HIGH
    assert mapped_suggestion.confidence_reason == suggestion.confidence_reason
    assert mapped_suggestion.created_at == suggestion.created_at
    assert mapped_suggestion.updated_at == suggestion.updated_at
