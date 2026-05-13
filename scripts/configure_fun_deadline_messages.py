from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, inspect, select, text

from app.db.database import Base, SessionLocal, engine
from app.db.models import (
    Deadline,
    NotificationJob,
    NotificationJobStatus,
    NotificationMediaAsset,
    NotificationMessageVariant,
    NotificationRule,
    VKChat,
)
from app.services.notification_job_service import create_jobs_for_deadline

MESSAGE_VARIANTS = {
    "greeting": [
    "Друзья, короткое напоминание.",
    "Ученики, держим фокус.",
    "Братья и сестры по подготовке, дедлайн близко.",
    "Команда, не откладываем на последний час.",
    "Ребята, сегодня тот самый день.",

    "Ребята, важное напоминание по домашке.",
    "Команда, проверяем дедлайны.",
    "Друзья, пора закрыть учебный долг.",
    "Ученики, не теряем темп.",
    "Ребята, фиксируем важную задачу.",
    "Команда, дедлайн уже рядом.",
    "Друзья, лучше сдать заранее, чем в последний момент.",
    "Ученики, держим учебный режим.",
    "Ребята, сегодня нужно быть особенно внимательными.",
    "Команда, напоминаю про важную сдачу.",
    "Друзья, домашка сама себя не сдаст.",
    "Ученики, маленький рывок — и задача закрыта.",
    "Ребята, не забываем про сегодняшнюю работу.",
    "Команда, время довести дело до конца.",
    "Друзья, спокойное напоминание без паники.",
],

"lead": [
    "{time_left} до дедлайна.",
    "Сегодня нужно закрыть эту домашку.",
    "Дедлайн уже на горизонте: лучше отправить заранее.",
    "Фиксирую важное напоминание по учебе.",
    "Пора довести задачу до статуса 'сдано'.",

    "До крайнего срока осталось {time_left}.",
    "Время до дедлайна: {time_left}.",
    "Работу лучше отправить заранее, пока есть запас времени.",
    "Сегодня важно не забыть про сдачу.",
    "Эта задача уже близко к дедлайну.",
    "Напоминаю: срок сдачи подходит к концу.",
    "Лучше закрыть работу сейчас, чем вспоминать о ней поздно вечером.",
    "Осталось немного времени, чтобы всё спокойно доделать.",
    "Дедлайн приближается, не откладываем.",
    "Сегодня хороший момент, чтобы поставить галочку 'готово'.",
    "Пора проверить, всё ли сделано и отправлено.",
    "Сейчас самое время вернуться к этой работе.",
    "Крайний срок уже близко.",
    "Не оставляем эту домашку на последний час.",
    "Проверяем работу и отправляем до дедлайна.",
],

"details": [
    "{subject}: {title}. Сдать до {deadline_at}. {description}",
    "Предмет: {subject}. Работа: {title}. Крайний срок: {deadline_at}. {description}",
    "{title} — дедлайн {deadline_at}. {description}",
    "По предмету {subject} сегодня дедлайн: {title}. До {deadline_at}. {description}",

    "Предмет: {subject}. Задание: {title}. Срок сдачи: {deadline_at}. {description}",
    "{subject} — {title}. Нужно сдать до {deadline_at}. {description}",
    "Работа: {title}. Предмет: {subject}. Дедлайн: {deadline_at}. {description}",
    "Напоминание по предмету {subject}: {title}. Крайний срок — {deadline_at}. {description}",
    "{title}. Сдать по предмету {subject} до {deadline_at}. {description}",
    "Сегодня по предмету {subject} нужно закрыть: {title}. Срок — {deadline_at}. {description}",
    "Домашняя работа: {title}. Предмет: {subject}. До сдачи: {deadline_at}. {description}",
    "Не забываем про {title} по предмету {subject}. Сдать до {deadline_at}. {description}",
    "Задача на сегодня: {title}. Предмет: {subject}. Крайний срок — {deadline_at}. {description}",
    "По {subject} осталось сдать работу: {title}. Дедлайн — {deadline_at}. {description}",
    "Проверяем и отправляем: {subject}, {title}. Срок сдачи — {deadline_at}. {description}",
],

"encouragement": [
    "Удачи, спокойно добиваем и сдаем.",
    "Вы справитесь. Главное — не тянуть до последней минуты.",
    "Любви, сил и аккуратных решений.",
    "Пусть сегодня всё сдастся легко.",
    "Сделайте маленький рывок, он окупится.",

    "Лучше сделать немного сейчас, чем срочно доделывать потом.",
    "Спокойно, по шагам — и работа будет закрыта.",
    "Главное — начать, дальше станет легче.",
    "Не обязательно идеально, важно вовремя и аккуратно.",
    "Соберитесь на короткий рывок, осталось немного.",
    "Проверьте ответы, оформление и отправку.",
    "Держим темп, вы уже близко к результату.",
    "Один дедлайн закрыт — меньше тревоги в голове.",
    "Работа не убежит, но дедлайн может. Лучше сдать сейчас.",
    "Сделайте аккуратно и отправьте без лишней спешки.",
    "Пусть это будет ещё одна закрытая задача в списке.",
    "Спокойная сдача лучше ночного марафона.",
    "Сейчас немного усилий — потом свободнее вечер.",
    "Не перегружайтесь, просто доведите до результата.",
    "Проверьте всё один раз и отправляйте.",
],

"footer": [
    "",
    "加油！今天也可以做到。",
    "Good luck, you have got this.",
    "Bonne chance, tout ira bien.",
    "¡Ánimo! Un paso más.",

    "Alles wird gut.",
    "One task at a time.",
    "Keep going, the finish line is close.",
    "Сделано вовремя — уже победа.",
    "Маленький шаг тоже считается.",
    "Закрываем дедлайн спокойно.",
    "Сегодня можно справиться.",
    "Главное — не бросать на финише.",
    "Пусть работа уйдёт в статус 'сдано'.",
    "Сначала сдаём, потом отдыхаем.",
],
}


def add_column_if_missing(table: str, column: str, ddl: str) -> None:
    inspector = inspect(engine)
    existing = {item["name"] for item in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def migrate_local_schema() -> None:
    Base.metadata.create_all(bind=engine)
    add_column_if_missing("notification_rules", "schedule_type", "VARCHAR(50) NOT NULL DEFAULT 'before_deadline'")
    add_column_if_missing("notification_rules", "send_time_local", "VARCHAR(5)")
    add_column_if_missing("notification_rules", "send_window_start_local", "VARCHAR(5)")
    add_column_if_missing("notification_rules", "send_window_end_local", "VARCHAR(5)")
    Base.metadata.create_all(bind=engine)


def seed_variants(db) -> int:
    created = 0
    for category, texts in MESSAGE_VARIANTS.items():
        for text_value in texts:
            exists = db.scalar(
                select(NotificationMessageVariant.id).where(
                    NotificationMessageVariant.category == category,
                    NotificationMessageVariant.text == text_value,
                )
            )
            if exists is not None:
                continue
            db.add(NotificationMessageVariant(category=category, text=text_value, weight=1, is_active=True))
            created += 1
    return created


def configure_daily_rule(db) -> NotificationRule:
    rule = db.scalar(select(NotificationRule).where(NotificationRule.title == "В день дедлайна, окно 13:00-15:00"))
    if rule is None:
        rule = NotificationRule(
            title="В день дедлайна, окно 13:00-15:00",
            send_before_minutes=0,
            schedule_type="deadline_day_window",
            send_time_local=None,
            send_window_start_local="13:00",
            send_window_end_local="15:00",
            text_template="#дедлайн\n{subject}: {title}. Сдать до {deadline_at}. {description}",
            is_active=True,
        )
        db.add(rule)
        db.flush()
    else:
        rule.send_before_minutes = 0
        rule.schedule_type = "deadline_day_window"
        rule.send_time_local = None
        rule.send_window_start_local = "13:00"
        rule.send_window_end_local = "15:00"
        rule.is_active = True
    return rule


def disable_old_relative_rules(db, daily_rule: NotificationRule) -> int:
    disabled = 0
    old_rules = db.scalars(
        select(NotificationRule).where(
            NotificationRule.id != daily_rule.id,
            NotificationRule.schedule_type != "deadline_day_window",
            NotificationRule.is_active.is_(True),
        )
    ).all()
    old_rule_ids = []
    for rule in old_rules:
        rule.is_active = False
        old_rule_ids.append(rule.id)
        disabled += 1
    db.flush()
    if old_rule_ids:
        db.query(NotificationJob).filter(
            NotificationJob.rule_id.in_(old_rule_ids),
            NotificationJob.status.in_([NotificationJobStatus.pending.value, NotificationJobStatus.retry.value]),
        ).delete(synchronize_session=False)
    inactive_rule_ids = [
        rule.id for rule in db.scalars(select(NotificationRule).where(NotificationRule.is_active.is_(False))).all()
    ]
    if inactive_rule_ids:
        db.query(NotificationJob).filter(
            NotificationJob.rule_id.in_(inactive_rule_ids),
            NotificationJob.status.in_([NotificationJobStatus.pending.value, NotificationJobStatus.retry.value]),
        ).delete(synchronize_session=False)
    return disabled


def create_daily_jobs(db) -> int:
    now = datetime.now()
    created = 0
    deadlines = db.scalars(select(Deadline).where(Deadline.deadline_at >= now)).all()
    for deadline in deadlines:
        created += create_jobs_for_deadline(db, deadline, skip_past_send_at=True)
    return created


def main() -> int:
    migrate_local_schema()
    with SessionLocal() as db:
        variants_created = seed_variants(db)
        daily_rule = configure_daily_rule(db)
        disabled_rules = disable_old_relative_rules(db, daily_rule)
        daily_jobs_created = create_daily_jobs(db)
        assets_count = db.scalar(select(func.count()).select_from(NotificationMediaAsset))
        general_chat = db.scalar(select(VKChat).where(VKChat.title == "General"))
        db.commit()

    print("variants_created:", variants_created)
    print("daily_rule_id:", daily_rule.id)
    print("disabled_relative_rules:", disabled_rules)
    print("daily_jobs_created:", daily_jobs_created)
    print("general_peer_id:", general_chat.peer_id if general_chat else None)
    print("media_assets:", assets_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
