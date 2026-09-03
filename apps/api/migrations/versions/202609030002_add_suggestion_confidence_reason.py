from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609030002"
down_revision: str | None = "202609030001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suggested_responses",
        sa.Column(
            "confidence_reason",
            sa.Text(),
            nullable=False,
            server_default="No trusted knowledge sources were retrieved for this ticket.",
        ),
    )
    op.create_check_constraint(
        "ck_suggested_responses_confidence_reason_not_blank",
        "suggested_responses",
        "length(trim(confidence_reason)) > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_suggested_responses_confidence_reason_not_blank",
        "suggested_responses",
        type_="check",
    )
    op.drop_column("suggested_responses", "confidence_reason")
