from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202608170001"
down_revision: str | None = "202608110001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_tier", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("product_area", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "length(trim(external_id)) > 0", name="ck_tickets_external_id_not_blank"
        ),
        sa.CheckConstraint(
            "length(trim(customer_name)) > 0", name="ck_tickets_customer_name_not_blank"
        ),
        sa.CheckConstraint(
            "length(trim(customer_tier)) > 0", name="ck_tickets_customer_tier_not_blank"
        ),
        sa.CheckConstraint("length(trim(subject)) > 0", name="ck_tickets_subject_not_blank"),
        sa.CheckConstraint(
            "length(trim(description)) > 0", name="ck_tickets_description_not_blank"
        ),
        sa.CheckConstraint(
            "product_area IN ('billing', 'security', 'support', 'api', 'product', 'legal')",
            name="ck_tickets_product_area",
        ),
        sa.CheckConstraint(
            "status IN "
            "('open', 'triaged', 'waiting_on_customer', 'waiting_on_support', "
            "'resolved', 'closed')",
            name="ck_tickets_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        sa.UniqueConstraint("external_id", name="uq_tickets_external_id"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_product_area", "tickets", ["product_area"])
    op.create_index("ix_tickets_customer_tier", "tickets", ["customer_tier"])


def downgrade() -> None:
    op.drop_index("ix_tickets_customer_tier", table_name="tickets")
    op.drop_index("ix_tickets_product_area", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
