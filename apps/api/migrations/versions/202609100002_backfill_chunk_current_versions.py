from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609100002"
down_revision: str | None = "202609100001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            update document_chunks dc
            set document_version_id = d.current_version_id
            from documents d
            where d.id = dc.document_id
              and d.current_version_id is not null
              and dc.document_version_id is null
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            update document_chunks dc
            set document_version_id = null
            from documents d
            where d.id = dc.document_id
              and d.current_version_id = dc.document_version_id
            """
        )
    )
