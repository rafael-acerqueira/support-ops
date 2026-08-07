from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202608070001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("product_area", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column("source_file_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_documents_name_not_blank"),
        sa.CheckConstraint("size_bytes > 0", name="ck_documents_size_bytes_positive"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_documents_chunk_count_non_negative"),
        sa.CheckConstraint(
            "document_type IN "
            "('internal_policy', 'sla_policy', 'security_policy', 'incident_policy', "
            "'playbook', 'faq', 'technical_documentation')",
            name="ck_documents_document_type",
        ),
        sa.CheckConstraint(
            "product_area IN ('billing', 'security', 'support', 'api', 'product', 'legal')",
            name="ck_documents_product_area",
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'failed')",
            name="ck_documents_status",
        ),
    )
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_product_area", "documents", ["product_area"])
    op.create_index("ix_documents_is_active", "documents", ["is_active"])
    op.create_index("ix_documents_tags", "documents", ["tags"], postgresql_using="gin")

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index_non_negative"),
        sa.CheckConstraint(
            "length(trim(content)) > 0", name="ck_document_chunks_content_not_blank"
        ),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"
        ),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_tags", table_name="documents", postgresql_using="gin")
    op.drop_index("ix_documents_is_active", table_name="documents")
    op.drop_index("ix_documents_product_area", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_table("documents")
