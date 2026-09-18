from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609100003"
down_revision: str | None = "202609100002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("""
            do $$
            begin
              if exists (
                select 1
                from document_chunks
                where document_version_id is null
              ) then
                raise exception
                  'Cannot require document_chunks.document_version_id while legacy chunks remain';
              end if;
            end $$;
            """))
    op.drop_index(
        "uq_document_chunks_document_version_id_chunk_index",
        table_name="document_chunks",
    )
    op.drop_constraint(
        "fk_document_chunks_document_version_id",
        "document_chunks",
        type_="foreignkey",
    )
    op.alter_column(
        "document_chunks",
        "document_version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_document_chunks_document_version_id",
        "document_chunks",
        "document_versions",
        ["document_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "uq_document_chunks_document_version_id_chunk_index",
        "document_chunks",
        ["document_version_id", "chunk_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_document_chunks_document_version_id_chunk_index",
        table_name="document_chunks",
    )
    op.drop_constraint(
        "fk_document_chunks_document_version_id",
        "document_chunks",
        type_="foreignkey",
    )
    op.alter_column(
        "document_chunks",
        "document_version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
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
        "uq_document_chunks_document_version_id_chunk_index",
        "document_chunks",
        ["document_version_id", "chunk_index"],
        unique=True,
        postgresql_where=sa.text("document_version_id is not null"),
    )
