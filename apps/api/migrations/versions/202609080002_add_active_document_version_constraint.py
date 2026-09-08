from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609080002"
down_revision: str | None = "202609080001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_document_versions_active_per_document",
        "document_versions",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_document_versions_active_per_document",
        table_name="document_versions",
        postgresql_where=sa.text("is_active = true"),
    )
