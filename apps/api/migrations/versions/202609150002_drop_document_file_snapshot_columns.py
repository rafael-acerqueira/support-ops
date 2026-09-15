"""Drop document file snapshot columns.

Revision ID: 202609150002
Revises: 202609150001
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609150002"
down_revision: str | None = "202609150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("documents", "size_bytes")
    op.drop_column("documents", "content_type")
    op.drop_column("documents", "storage_key")
    op.drop_column("documents", "source_file_name")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_file_name", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("content_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
    )
