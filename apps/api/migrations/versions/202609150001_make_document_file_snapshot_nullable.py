"""Make document file snapshot nullable.

Revision ID: 202609150001
Revises: 202609100003
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202609150001"
down_revision: str | None = "202609100003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "documents",
        "source_file_name",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.alter_column(
        "documents",
        "content_type",
        existing_type=sa.String(length=128),
        nullable=True,
    )
    op.alter_column(
        "documents",
        "size_bytes",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE documents SET source_file_name = name WHERE source_file_name IS NULL")
    op.execute(
        "UPDATE documents SET content_type = 'application/octet-stream' "
        "WHERE content_type IS NULL"
    )
    op.execute("UPDATE documents SET size_bytes = 1 WHERE size_bytes IS NULL")

    op.alter_column(
        "documents",
        "size_bytes",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "documents",
        "content_type",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "documents",
        "source_file_name",
        existing_type=sa.String(length=512),
        nullable=False,
    )
