"""message variants and daily rules

Revision ID: 0002_message_variants
Revises: 0001_initial
Create Date: 2026-05-06 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_message_variants"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_rules",
        sa.Column("schedule_type", sa.String(length=50), server_default="before_deadline", nullable=False),
    )
    op.add_column("notification_rules", sa.Column("send_time_local", sa.String(length=5), nullable=True))
    op.add_column("notification_rules", sa.Column("send_window_start_local", sa.String(length=5), nullable=True))
    op.add_column("notification_rules", sa.Column("send_window_end_local", sa.String(length=5), nullable=True))
    op.create_table(
        "notification_message_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_message_variants_category"), "notification_message_variants", ["category"])
    op.create_table(
        "notification_media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("attachment", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_media_assets")
    op.drop_index(op.f("ix_notification_message_variants_category"), table_name="notification_message_variants")
    op.drop_table("notification_message_variants")
    op.drop_column("notification_rules", "send_time_local")
    op.drop_column("notification_rules", "send_window_start_local")
    op.drop_column("notification_rules", "send_window_end_local")
    op.drop_column("notification_rules", "schedule_type")
