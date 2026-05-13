from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Deadline, NotificationMediaAsset, NotificationMessageVariant


@dataclass
class ComposedMessage:
    text: str
    attachment: str | None = None


def weighted_choice(items):
    if not items:
        return None
    return random.choices(items, weights=[max(item.weight, 1) for item in items], k=1)[0]


def format_deadline_at(deadline: Deadline) -> str:
    return deadline.deadline_at.strftime("%d.%m.%Y %H:%M")


def time_left_text(deadline: Deadline) -> str:
    delta = deadline.deadline_at.replace(tzinfo=None) - datetime.now().replace(tzinfo=None)
    hours = max(int(delta.total_seconds() // 3600), 0)
    if hours >= 24:
        days = hours // 24
        return f"осталось примерно {days} дн."
    return f"осталось примерно {hours} ч."


def compose_deadline_message(db: Session, deadline: Deadline) -> ComposedMessage:
    variants = db.scalars(
        select(NotificationMessageVariant).where(NotificationMessageVariant.is_active.is_(True))
    ).all()
    by_category: dict[str, list[NotificationMessageVariant]] = {}
    for item in variants:
        by_category.setdefault(item.category, []).append(item)

    values = {
        "subject": deadline.subject or "предмет",
        "title": deadline.title,
        "description": deadline.description or "",
        "deadline_at": format_deadline_at(deadline),
        "time_left": time_left_text(deadline),
    }

    lines = ["#дедлайн"]
    for category in ("greeting", "lead", "details", "encouragement", "footer"):
        item = weighted_choice(by_category.get(category, []))
        if item is not None:
            lines.append(item.text.format(**values))

    if len(lines) == 1:
        lines.append(
            "Друзья, дедлайн по предмету {subject}: {title}. Сдать до {deadline_at}. {description}".format(**values)
        )

    assets = db.scalars(select(NotificationMediaAsset).where(NotificationMediaAsset.is_active.is_(True))).all()
    attachment = None
    if assets and random.random() < 0.25:
        attachment = weighted_choice(assets).attachment

    return ComposedMessage(text="\n".join(line for line in lines if line.strip()).strip(), attachment=attachment)
