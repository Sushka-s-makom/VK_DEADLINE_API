"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vk_communities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("vk_group_id", sa.BigInteger(), nullable=False),
        sa.Column("token_env_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vk_group_id"),
    )
    op.create_table(
        "study_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("external_group_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_group_id"),
    )
    op.create_table(
        "notification_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("send_before_minutes", sa.Integer(), nullable=False),
        sa.Column("text_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vk_chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_group_id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column("peer_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["vk_communities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["study_group_id"], ["study_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "peer_id", name="uq_vk_chats_community_peer"),
    )
    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_group_id", sa.Integer(), nullable=False),
        sa.Column("external_deadline_id", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["study_group_id"], ["study_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_group_id", "external_deadline_id", name="uq_deadlines_study_group_external"),
    )
    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deadline_id", sa.Integer(), nullable=False),
        sa.Column("vk_chat_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("vk_message_id", sa.BigInteger(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["notification_rules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vk_chat_id"], ["vk_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deadline_id", "vk_chat_id", "rule_id", name="uq_notification_jobs_deadline_chat_rule"),
    )
    op.create_index(op.f("ix_notification_jobs_send_at"), "notification_jobs", ["send_at"], unique=False)
    op.create_index(op.f("ix_notification_jobs_status"), "notification_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_jobs_status"), table_name="notification_jobs")
    op.drop_index(op.f("ix_notification_jobs_send_at"), table_name="notification_jobs")
    op.drop_table("notification_jobs")
    op.drop_table("deadlines")
    op.drop_table("vk_chats")
    op.drop_table("notification_rules")
    op.drop_table("study_groups")
    op.drop_table("vk_communities")
