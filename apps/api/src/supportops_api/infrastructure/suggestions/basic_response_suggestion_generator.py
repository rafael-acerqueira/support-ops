from __future__ import annotations

from supportops_api.application.response_suggestions import (
    GeneratedSuggestedResponse,
    ResponseSuggestionGenerator,
)
from supportops_api.domain.tickets import Ticket


class BasicResponseSuggestionGenerator(ResponseSuggestionGenerator):
    async def generate(self, ticket: Ticket) -> GeneratedSuggestedResponse:
        content = (
            f"Hi {ticket.customer_name},\n\n"
            f"Thanks for reaching out about {ticket.subject.lower()}. "
            "We reviewed the request and will follow the applicable internal policy for this case.\n\n"
            "Next steps:\n"
            "1. Validate the account and impacted product area.\n"
            "2. Check the relevant support policy before taking action.\n"
            "3. Reply with the approved resolution or escalation path.\n\n"
            "Best,\nSupportOps"
        )
        sources = [
            {
                "document_name": f"{ticket.product_area.value}-playbook.md",
                "document_type": "Playbook",
                "relevance_score": 0.82,
                "excerpt": "Validate the customer request against the relevant support playbook before confirming next steps.",
            },
            {
                "document_name": "internal-support-policy.md",
                "document_type": "Policy",
                "relevance_score": 0.76,
                "excerpt": "Support agents should avoid policy commitments until the account and impact are verified.",
            },
        ]
        return GeneratedSuggestedResponse(content=content, sources=sources)
