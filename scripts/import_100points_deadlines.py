"""Import homework deadlines from 100points.ru courses.

API base: https://api.100points.ru/api
Auth:     POST /login  → {"token": "..."}  (Bearer)
Courses:  POST /student/courses/{id}/lessons  → {course_title, lessons[].deadline}

Each course gets its own StudyGroup in the DB (external_group_id = "100points:course:<id>").
VK peer IDs per course are configured via POINTS100_COURSE_CHATS env var:
  POINTS100_COURSE_CHATS=1872:2000000001,2536:2000000002,2850:2000000003
If a course is not listed there, POINTS100_DEFAULT_PEER_ID (or 2000000002) is used.

Required env vars: POINTS100_EMAIL, POINTS100_PASSWORD, POINTS100_COURSE_IDS
Optional:          POINTS100_COURSE_CHATS, POINTS100_DEFAULT_PEER_ID, DATABASE_URL
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
from datetime import datetime, timedelta, timezone
from urllib import request, error as url_error

import certifi
from dotenv import load_dotenv
from sqlalchemy import select

from app.db.database import Base, SessionLocal, engine
from app.db.models import Deadline, NotificationRule, StudyGroup, VKChat, VKCommunity
from app.services.notification_job_service import create_jobs_for_deadline

load_dotenv()

API_BASE = "https://api.100points.ru/api"
SUBJECT = "Физика"
TEXT_TEMPLATE = "#дедлайн\n{subject}: {title}. Сдать до {deadline_at}. {description}"

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_MSK = timezone(timedelta(hours=3))


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api(path: str, *, method: str = "GET", body: dict | None = None, token: str | None = None) -> dict | list:
    url = f"{API_BASE}{path}"
    data = json.dumps(body or {}).encode() if body is not None or method == "POST" else None
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except url_error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {body_text[:200]}") from exc


def login(email: str, password: str) -> str:
    result = _api("/login", method="POST", body={"email": email, "password": password})
    token = result.get("token")
    if not token:
        raise RuntimeError(f"Login failed: {result}")
    return token


def fetch_course(course_id: int, token: str) -> tuple[str, list[dict]]:
    """Returns (course_title, lessons)."""
    result = _api(f"/student/courses/{course_id}/lessons", method="POST", body={}, token=token)
    if isinstance(result, dict) and result.get("status") == "fail":
        raise RuntimeError(f"Course {course_id}: {result.get('message')}")
    title = result.get("course_title") or f"Курс {course_id}"
    return title, result.get("lessons", [])


def parse_deadline(value: str | None) -> datetime | None:
    if not value:
        return None
    # ISO 8601 (UTC)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Russian locale: "23.05.2026 23:59" — Moscow time (UTC+3)
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=_MSK).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------

def _parse_course_chats() -> dict[int, int]:
    """Parse POINTS100_COURSE_CHATS=1872:2000000001,2536:2000000002 → {1872: 2000000001, ...}"""
    raw = os.environ.get("POINTS100_COURSE_CHATS", "")
    result: dict[int, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            cid, pid = pair.split(":", 1)
            try:
                result[int(cid.strip())] = int(pid.strip())
            except ValueError:
                pass
    return result


def ensure_community_and_rule(db) -> tuple[VKCommunity, NotificationRule]:
    Base.metadata.create_all(bind=engine)

    community = db.scalar(select(VKCommunity).where(VKCommunity.token_env_name == "VK_GROUP_TOKEN"))
    if community is None:
        community = VKCommunity(
            title="VK MVP Community",
            vk_group_id=123456789,
            token_env_name="VK_GROUP_TOKEN",
            is_active=True,
        )
        db.add(community)
        db.flush()

    rule = db.scalar(select(NotificationRule).where(NotificationRule.title == "В день дедлайна, окно 13:00-15:00"))
    if rule is None:
        rule = NotificationRule(
            title="В день дедлайна, окно 13:00-15:00",
            send_before_minutes=0,
            schedule_type="deadline_day_window",
            send_time_local=None,
            send_window_start_local="13:00",
            send_window_end_local="15:00",
            text_template=TEXT_TEMPLATE,
            is_active=True,
        )
        db.add(rule)
        db.flush()

    return community, rule


def ensure_course_group(
    db,
    community: VKCommunity,
    course_id: int,
    course_title: str,
    peer_id: int,
) -> tuple[StudyGroup, VKChat]:
    external_group_id = f"100points:course:{course_id}"

    study_group = db.scalar(select(StudyGroup).where(StudyGroup.external_group_id == external_group_id))
    if study_group is None:
        study_group = StudyGroup(
            title=course_title,
            subject=SUBJECT,
            external_group_id=external_group_id,
            is_active=True,
        )
        db.add(study_group)
        db.flush()
    else:
        study_group.title = course_title

    chat = db.scalar(
        select(VKChat).where(VKChat.community_id == community.id, VKChat.peer_id == peer_id)
    )
    if chat is None:
        chat = VKChat(
            study_group_id=study_group.id,
            community_id=community.id,
            peer_id=peer_id,
            title=course_title,
            is_active=True,
        )
        db.add(chat)
        db.flush()
    elif chat.study_group_id != study_group.id:
        # Re-link if chat was previously attached to a different group
        chat.study_group_id = study_group.id

    return study_group, chat


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------

def import_from_course(
    db,
    study_group: StudyGroup,
    course_id: int,
    lessons: list[dict],
    include_past: bool,
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    imported = updated = skipped_past = skipped_no_deadline = jobs_created = 0

    for lesson in lessons:
        lesson_id = lesson["id"]
        title = lesson.get("title") or f"Урок {lesson.get('number', lesson_id)}"
        deadline_at = parse_deadline(lesson.get("deadline"))

        if deadline_at is None:
            skipped_no_deadline += 1
            continue
        if deadline_at <= now and not include_past:
            skipped_past += 1
            continue

        external_id = f"100points:course{course_id}:lesson{lesson_id}"
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
                description=f"100points.ru — курс {course_id}",
                deadline_at=deadline_at,
                source="api",
            )
            db.add(deadline)
            db.flush()
            imported += 1
        else:
            deadline.title = title
            deadline.deadline_at = deadline_at
            updated += 1

        jobs_created += create_jobs_for_deadline(db, deadline, skip_past_send_at=True)

    return {
        "imported": imported,
        "updated": updated,
        "skipped_past": skipped_past,
        "skipped_no_deadline": skipped_no_deadline,
        "jobs_created": jobs_created,
    }


def import_deadlines(course_ids: list[int], include_past: bool = False) -> dict[str, int]:
    email = os.environ["POINTS100_EMAIL"]
    password = os.environ["POINTS100_PASSWORD"]
    default_peer_id = int(os.environ.get("POINTS100_DEFAULT_PEER_ID", "2000000002"))
    course_chats = _parse_course_chats()

    print(f"Logging in as {email}...")
    token = login(email, password)

    totals: dict[str, int] = {"imported": 0, "updated": 0, "skipped_past": 0, "skipped_no_deadline": 0, "jobs_created": 0}

    with SessionLocal() as db:
        community, _rule = ensure_community_and_rule(db)

        for course_id in course_ids:
            print(f"\nCourse {course_id}:")
            try:
                course_title, lessons = fetch_course(course_id, token)
            except RuntimeError as exc:
                print(f"  SKIP: {exc}")
                continue

            peer_id = course_chats.get(course_id, default_peer_id)
            print(f"  Title : {course_title}")
            print(f"  Lessons: {len(lessons)}  |  peer_id: {peer_id}")

            study_group, _chat = ensure_course_group(db, community, course_id, course_title, peer_id)
            stats = import_from_course(db, study_group, course_id, lessons, include_past)
            print(f"  imported={stats['imported']} updated={stats['updated']} "
                  f"no_deadline={stats['skipped_no_deadline']} past={stats['skipped_past']} jobs={stats['jobs_created']}")
            for k, v in stats.items():
                totals[k] = totals.get(k, 0) + v

        db.commit()

    return totals


def show_groups(db) -> None:
    """Print current course→group→chat mapping."""
    groups = db.scalars(
        select(StudyGroup).where(StudyGroup.external_group_id.like("100points:course:%"))
    ).all()
    if not groups:
        print("No 100points course groups found in DB.")
        return
    print(f"\n{'='*70}")
    print(f"{'Курс (StudyGroup)':<45} {'external_group_id':<30} {'peer_ids'}")
    print(f"{'='*70}")
    for g in groups:
        peer_ids = [str(c.peer_id) for c in g.vk_chats]
        print(f"{g.title[:44]:<45} {g.external_group_id:<30} {', '.join(peer_ids) or '—'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Import deadlines from 100points.ru")
    parser.add_argument("--include-past", action="store_true", help="Import past deadlines too.")
    parser.add_argument("--course-ids", help="Comma-separated course IDs (overrides POINTS100_COURSE_IDS).")
    parser.add_argument("--show-groups", action="store_true", help="Print course→group→chat mapping and exit.")
    args = parser.parse_args()

    if args.show_groups:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            show_groups(db)
        return 0

    raw_ids = args.course_ids or os.environ.get("POINTS100_COURSE_IDS", "")
    course_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip()]
    if not course_ids:
        print("No course IDs configured. Set POINTS100_COURSE_IDS or pass --course-ids.")
        return 1

    result = import_deadlines(course_ids, include_past=args.include_past)
    print("\nTotal:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())