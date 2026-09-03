from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609030001"
down_revision: str | None = "202609010001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suggested_responses",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "suggested_responses",
        sa.Column(
            "confidence_level",
            sa.String(length=32),
            nullable=False,
            server_default="low",
        ),
    )
    op.create_check_constraint(
        "ck_suggested_responses_confidence_score",
        "suggested_responses",
        "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
    )
    op.create_check_constraint(
        "ck_suggested_responses_confidence_level",
        "suggested_responses",
        "confidence_level IN ('low', 'medium', 'high')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_suggested_responses_confidence_level",
        "suggested_responses",
        type_="check",
    )
    op.drop_constraint(
        "ck_suggested_responses_confidence_score",
        "suggested_responses",
        type_="check",
    )
    op.drop_column("suggested_responses", "confidence_level")
    op.drop_column("suggested_responses", "confidence_score")
