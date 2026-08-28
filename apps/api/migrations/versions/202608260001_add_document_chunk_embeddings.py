from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202608260001"
down_revision: str | None = "202608180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")


def downgrade() -> None:
    op.execute("ALTER TABLE document_chunks DROP COLUMN embedding")
