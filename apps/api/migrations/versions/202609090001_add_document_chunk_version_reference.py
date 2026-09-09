from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609090001"
down_revision: str | None = "202609080002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_chunks_document_version_id",
        "document_chunks",
        "document_versions",
        ["document_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_document_chunks_document_version_id",
        "document_chunks",
        ["document_version_id"],
    )
    op.execute(
        """
        update document_chunks dc
        set document_version_id = dv.id
        from document_versions dv
        where dv.document_id = dc.document_id
          and dv.is_active = true
          and dc.document_version_id is null
        """
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_version_id", table_name="document_chunks")
    op.drop_constraint(
        "fk_document_chunks_document_version_id",
        "document_chunks",
        type_="foreignkey",
    )
    op.drop_column("document_chunks", "document_version_id")
