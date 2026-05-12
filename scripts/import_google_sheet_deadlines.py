from __future__ import annotations

import argparse
import csv
import io
import ssl
import urllib.request
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
import certifi

from app.db.database import Base, SessionLocal, engine
from app.db.models import Deadline, NotificationRule, StudyGroup, VKChat, VKCommunity
from app.services.notification_job_service import create_jobs_for_deadline

SHEET_ID = "1E5EHcFJdH7A4UI1GxmUw4FgIsosfQd-PlNFJ316I4Qk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
GENERAL_PEER_ID = 2000000002
DEFAULT_TZ = ZoneInfo("Europe/Moscow")
DEFAULT_DEADLINE_TIME = time(hour=18, minute=0)
TEXT_TEMPLATE = "#дедлайн\n{subject}: {title}. Сдать до {deadline_at}. {description}"


def load_csv_rows(url: str = CSV_URL) -> list[list[str]]:
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, timeout=20, context=context) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            return datetime.combine(parsed, DEFAULT_DEADLINE_TIME, tzinfo=DEFAULT_TZ)
        except ValueError:
            continue
    return None


def ensure_base_data(db) -> tuple[StudyGroup, VKChat]:
    Base.metadata.create_all(bind=engine)

    community = db.scalar(select(VKCommunity).where(VKCommunity.vk_group_id == 123456789))
    if community is None:
        community = VKCommunity(
            title="VK MVP Community",
            vk_group_id=123456789,
            token_env_name="VK_GROUP_TOKEN",
            is_active=True,
        )
        db.add(community)
        db.flush()

    study_group = db.scalar(select(StudyGroup).where(StudyGroup.external_group_id == "eb-046"))
    if study_group is None:
        study_group = StudyGroup(
            title="Группа eb-046",
            subject="Физика",
            external_group_id="eb-046",
            is_active=True,
        )
        db.add(study_group)
        db.flush()

    chat = db.scalar(select(VKChat).where(VKChat.community_id == community.id, VKChat.peer_id == GENERAL_PEER_ID))
    if chat is None:
        chat = VKChat(
            study_group_id=study_group.id,
            community_id=community.id,
            peer_id=GENERAL_PEER_ID,
            title="General",
            is_active=True,
        )
        db.add(chat)
        db.flush()

    rule = db.scalar(select(NotificationRule).where(NotificationRule.title == "В день дедлайна, окно 13:00-15:00"))
    if rule is None:
        db.add(
            NotificationRule(
                title="В день дедлайна, окно 13:00-15:00",
                send_before_minutes=0,
                schedule_type="deadline_day_window",
                send_time_local=None,
                send_window_start_local="13:00",
                send_window_end_local="15:00",
                text_template=TEXT_TEMPLATE,
                is_active=True,
            )
        )
    else:
        rule.send_before_minutes = 0
        rule.schedule_type = "deadline_day_window"
        rule.send_time_local = None
        rule.send_window_start_local = "13:00"
        rule.send_window_end_local = "15:00"
        rule.is_active = True

    db.flush()
    return study_group, chat


def import_deadlines(include_past: bool = False) -> dict[str, int]:
    rows = load_csv_rows()
    if len(rows) < 4:
        raise RuntimeError("Google Sheet has fewer than 4 rows")

    titles_row = rows[0]
    deadlines_row = rows[3]
    now = datetime.now(DEFAULT_TZ)

    imported = 0
    skipped_past = 0
    skipped_invalid = 0
    jobs_created = 0

    with SessionLocal() as db:
        study_group, _chat = ensure_base_data(db)

        # H column is index 7. Titles are in row 1, deadlines are in row 4.
        for col_index in range(7, max(len(titles_row), len(deadlines_row))):
            title = titles_row[col_index].strip() if col_index < len(titles_row) else ""
            raw_deadline = deadlines_row[col_index].strip() if col_index < len(deadlines_row) else ""
            deadline_at = parse_date(raw_deadline)

            if not title or deadline_at is None:
                skipped_invalid += 1
                continue
            if deadline_at <= now and not include_past:
                skipped_past += 1
                continue

            external_id = f"{SHEET_ID}:row4:col{col_index + 1}"
            deadline = db.scalar(
                select(Deadline).where(
                    Deadline.study_group_id == study_group.id,
                    Deadline.external_deadline_id == external_id,
                )
            )
            if deadline is None:
                deadline = Deadline(
                    study_group_id=study_group.id,
                    external_deadline_id=external_id,
                    subject=study_group.subject,
                    title=title,
                    description=f"Дедлайн из Google Sheets: {raw_deadline}",
                    deadline_at=deadline_at,
                    source="google_sheets",
                )
                db.add(deadline)
                db.flush()
                imported += 1
            else:
                deadline.title = title
                deadline.description = f"Дедлайн из Google Sheets: {raw_deadline}"
                deadline.deadline_at = deadline_at

            jobs_created += create_jobs_for_deadline(db, deadline, skip_past_send_at=True)

        db.commit()

    return {
        "imported": imported,
        "jobs_created": jobs_created,
        "skipped_past": skipped_past,
        "skipped_invalid": skipped_invalid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-past", action="store_true", help="Import past deadlines too.")
    args = parser.parse_args()
    result = import_deadlines(include_past=args.include_past)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
