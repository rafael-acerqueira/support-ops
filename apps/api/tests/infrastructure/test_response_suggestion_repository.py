from uuid import uuid4

from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
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
    )
    suggestion.approve()

    record = _suggestion_to_record(suggestion)
    mapped_suggestion = _record_to_suggestion(record)

    assert mapped_suggestion.id == suggestion.id
    assert mapped_suggestion.ticket_id == suggestion.ticket_id
    assert mapped_suggestion.content == "Draft reply"
    assert mapped_suggestion.status == SuggestedResponseStatus.APPROVED
    assert mapped_suggestion.sources == suggestion.sources
    assert mapped_suggestion.created_at == suggestion.created_at
    assert mapped_suggestion.updated_at == suggestion.updated_at
