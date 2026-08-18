from __future__ import annotations

from supportops_api.application.response_suggestions import ResponseSuggestionGenerator
from supportops_api.domain.tickets import Ticket


class BasicResponseSuggestionGenerator(ResponseSuggestionGenerator):
    async def generate(self, ticket: Ticket) -> str:
        return (
            f"Hi {ticket.customer_name},\n\n"
            f"Thanks for reaching out about {ticket.subject.lower()}. "
            "We reviewed the request and will follow the applicable internal policy for this case.\n\n"
            "Next steps:\n"
            "1. Validate the account and impacted product area.\n"
            "2. Check the relevant support policy before taking action.\n"
            "3. Reply with the approved resolution or escalation path.\n\n"
            "Best,\nSupportOps"
        )
