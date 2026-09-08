from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609080001"
down_revision: str | None = "202609070001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_file_name", sa.String(length=512), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(trim(version)) > 0", name="ck_document_versions_version"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'failed')",
            name="ck_document_versions_status",
        ),
        sa.CheckConstraint("length(trim(source_file_name)) > 0", name="ck_document_versions_file"),
        sa.CheckConstraint("length(trim(storage_key)) > 0", name="ck_document_versions_storage"),
        sa.CheckConstraint("length(trim(content_type)) > 0", name="ck_document_versions_content"),
        sa.CheckConstraint("size_bytes > 0", name="ck_document_versions_size"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_document_versions_chunk_count"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "version", name="uq_document_versions_document_version"),
    )
    op.create_index(
        "ix_document_versions_document_id", "document_versions", ["document_id"]
    )
    op.create_index("ix_document_versions_status", "document_versions", ["status"])
    op.create_index("ix_document_versions_is_active", "document_versions", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_document_versions_is_active", table_name="document_versions")
    op.drop_index("ix_document_versions_status", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
