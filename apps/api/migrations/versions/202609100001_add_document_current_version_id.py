from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609100001"
down_revision: str | None = "202609090003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_documents_current_version_id",
        "documents",
        ["current_version_id"],
    )
    op.create_foreign_key(
        "fk_documents_current_version_id_document_versions",
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        sa.text(
            """
            update documents
            set current_version_id = matched_versions.id
            from (
                select distinct on (v.document_id) v.document_id, v.id
                from document_versions v
                join documents d on d.id = v.document_id
                where v.version = d.version
                  and v.storage_key = d.storage_key
                order by v.document_id, v.created_at desc
            ) as matched_versions
            where documents.id = matched_versions.document_id
              and documents.current_version_id is null
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_documents_current_version_id_document_versions",
        "documents",
        type_="foreignkey",
    )
    op.drop_index("ix_documents_current_version_id", table_name="documents")
    op.drop_column("documents", "current_version_id")
