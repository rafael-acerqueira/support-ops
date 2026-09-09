from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609090003"
down_revision: str | None = "202609090002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_document_chunks_document_id_chunk_index",
        "document_chunks",
        type_="unique",
    )
    op.create_index(
        "uq_document_chunks_document_version_id_chunk_index",
        "document_chunks",
        ["document_version_id", "chunk_index"],
        unique=True,
        postgresql_where=sa.text("document_version_id is not null"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_document_chunks_document_version_id_chunk_index",
        table_name="document_chunks",
        postgresql_where=sa.text("document_version_id is not null"),
    )
    op.create_unique_constraint(
        "uq_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )
