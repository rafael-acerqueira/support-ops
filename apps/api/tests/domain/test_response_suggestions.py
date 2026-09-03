from uuid import uuid4

import pytest

from supportops_api.domain.response_suggestions import (
    SuggestedResponse,
    SuggestedResponseConfidenceLevel,
    SuggestedResponseStatus,
)


def test_create_suggested_response_trims_content() -> None:
    ticket_id = uuid4()

    suggestion = SuggestedResponse.create(ticket_id=ticket_id, content=" Draft reply ")

    assert suggestion.ticket_id == ticket_id
    assert suggestion.content == "Draft reply"
    assert suggestion.status == SuggestedResponseStatus.DRAFT
    assert suggestion.sources == []
    assert suggestion.confidence_score is None
    assert suggestion.confidence_level == SuggestedResponseConfidenceLevel.LOW


def test_create_suggested_response_accepts_confidence() -> None:
    suggestion = SuggestedResponse.create(
        ticket_id=uuid4(),
        content="Draft reply",
        confidence_score=0.91,
        confidence_level=SuggestedResponseConfidenceLevel.HIGH,
    )

    assert suggestion.confidence_score == 0.91
    assert suggestion.confidence_level == SuggestedResponseConfidenceLevel.HIGH


def test_suggested_response_rejects_invalid_confidence_score() -> None:
    with pytest.raises(ValueError, match="confidence score must be between 0 and 1"):
        SuggestedResponse.create(
            ticket_id=uuid4(),
            content="Draft reply",
            confidence_score=1.1,
        )


def test_suggested_response_requires_content() -> None:
    with pytest.raises(ValueError, match="Suggested response content is required"):
        SuggestedResponse.create(ticket_id=uuid4(), content="   ")


def test_approve_and_reject_update_status() -> None:
    suggestion = SuggestedResponse.create(ticket_id=uuid4(), content="Draft reply")

    suggestion.approve()
    assert suggestion.status == SuggestedResponseStatus.APPROVED

    suggestion.reject()
    assert suggestion.status == SuggestedResponseStatus.REJECTED
