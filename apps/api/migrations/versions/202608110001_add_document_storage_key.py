from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202608110001"
down_revision: str | None = "202608070001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("storage_key", sa.String(length=1024), nullable=True))
    op.create_index("ix_documents_storage_key", "documents", ["storage_key"])


def downgrade() -> None:
    op.drop_index("ix_documents_storage_key", table_name="documents")
    op.drop_column("documents", "storage_key")
