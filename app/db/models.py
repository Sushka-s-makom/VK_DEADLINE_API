from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DeadlineSource(StrEnum):
    manual = "manual"
    api = "api"
    csv = "csv"
    google_sheets = "google_sheets"


class NotificationJobStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    sent = "sent"
    failed = "failed"
    retry = "retry"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VKCommunity(TimestampMixin, Base):
    __tablename__ = "vk_communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vk_group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    token_env_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    vk_chats: Mapped[list[VKChat]] = relationship(back_populates="community")


class StudyGroup(TimestampMixin, Base):
    __tablename__ = "study_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_group_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    vk_chats: Mapped[list[VKChat]] = relationship(back_populates="study_group")
    deadlines: Mapped[list[Deadline]] = relationship(back_populates="study_group")


class VKChat(TimestampMixin, Base):
    __tablename__ = "vk_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False)
    community_id: Mapped[int] = mapped_column(ForeignKey("vk_communities.id", ondelete="RESTRICT"), nullable=False)
    peer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    study_group: Mapped[StudyGroup] = relationship(back_populates="vk_chats")
    community: Mapped[VKCommunity] = relationship(back_populates="vk_chats")
    notification_jobs: Mapped[list[NotificationJob]] = relationship(back_populates="vk_chat")

    __table_args__ = (UniqueConstraint("community_id", "peer_id", name="uq_vk_chats_community_peer"),)


class Deadline(TimestampMixin, Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False)
    external_deadline_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default=DeadlineSource.manual.value, server_default="manual")

    study_group: Mapped[StudyGroup] = relationship(back_populates="deadlines")
    notification_jobs: Mapped[list[NotificationJob]] = relationship(back_populates="deadline")

    __table_args__ = (UniqueConstraint("study_group_id", "external_deadline_id", name="uq_deadlines_study_group_external"),)


class NotificationRule(TimestampMixin, Base):
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    send_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="before_deadline", server_default="before_deadline")
    send_time_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    send_window_start_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    send_window_end_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    text_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    notification_jobs: Mapped[list[NotificationJob]] = relationship(back_populates="rule")


class NotificationMessageVariant(TimestampMixin, Base):
    __tablename__ = "notification_message_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class NotificationMediaAsset(TimestampMixin, Base):
    __tablename__ = "notification_media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    attachment: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class NotificationJob(TimestampMixin, Base):
    __tablename__ = "notification_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    deadline_id: Mapped[int] = mapped_column(ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False)
    vk_chat_id: Mapped[int] = mapped_column(ForeignKey("vk_chats.id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[int] = mapped_column(ForeignKey("notification_rules.id", ondelete="RESTRICT"), nullable=False)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=NotificationJobStatus.pending.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    vk_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deadline: Mapped[Deadline] = relationship(back_populates="notification_jobs")
    vk_chat: Mapped[VKChat] = relationship(back_populates="notification_jobs")
    rule: Mapped[NotificationRule] = relationship(back_populates="notification_jobs")

    __table_args__ = (UniqueConstraint("deadline_id", "vk_chat_id", "rule_id", name="uq_notification_jobs_deadline_chat_rule"),)
