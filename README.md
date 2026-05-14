# VK Deadline API

Backend-сервис для VK-бота уведомлений онлайн-школы. MVP хранит учебные группы, VK-беседы, дедлайны, правила уведомлений и задачи отправки. Ученики не хранятся, личные сообщения ученикам не отправляются: основная связка `study_group -> vk_chat -> peer_id`.

## Стек

- Python, FastAPI, Pydantic
- PostgreSQL, SQLAlchemy, Alembic
- Redis, Celery worker, Celery beat
- VK API `messages.send`
- Docker Compose

## Локальный запуск без Docker

Создайте окружение на Python 3.12:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

В `.env` для локального MVP:

```env
DATABASE_URL=sqlite:///./vk_deadline.db
REDIS_URL=redis://localhost:6379/0
VK_GROUP_TOKEN=your_vk_group_token
```

Найти `peer_id` беседы `General`:

```bash
.venv/bin/python scripts/find_vk_peer.py
```

Импортировать дедлайны из Google Sheets. Скрипт читает темы из строки 1 начиная с `H1`, дедлайны из строки 4 начиная с `H4`, создаёт группу `Группа eb-046`, чат `General` с `peer_id=2000000002`, правила уведомлений и `notification_jobs`.

```bash
.venv/bin/python -m scripts.import_google_sheet_deadlines
```

По умолчанию прошедшие дедлайны пропускаются. Чтобы импортировать и прошлые даты:

```bash
.venv/bin/python -m scripts.import_google_sheet_deadlines --include-past
```

Запустить API локально:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Разово обработать наступившие задачи без Celery/Redis:

```bash
.venv/bin/python -m scripts.send_due_notifications
```

Проверить, что было бы обработано, без реальной отправки:

```bash
.venv/bin/python -m scripts.send_due_notifications --dry-run
```

Переключить MVP на живые сообщения и отправку в день дедлайна в окне `13:00-15:00 MSK`:

```bash
.venv/bin/python -m scripts.configure_fun_deadline_messages
```

После этого активным остаётся правило `В день дедлайна, окно 13:00-15:00`, а текст каждого реального сообщения начинается с `#дедлайн` и собирается из случайных фраз. Для каждой пары `deadline + vk_chat + rule` время внутри окна считается стабильным hash-offset, поэтому при переимпорте оно не прыгает.

Добавить картинку можно через готовый VK attachment, например `photo-123456_789012`:

```bash
.venv/bin/python -m scripts.add_vk_media_asset photo-123456_789012 --title "Deadline image"
```

При отправке бот иногда добавит такую картинку к сообщению.

Запустить простой локальный scheduler без Docker/Celery:

```bash
.venv/bin/python -m scripts.run_local_scheduler
```

Он раз в минуту отправляет наступившие уведомления, а раз в час переимпортирует Google Sheets.

Проверить состояние MVP:

```bash
.venv/bin/python -m scripts.diagnose_mvp
```

Диагностика показывает количество дедлайнов, статусы jobs, ближайшие отправки, активное правило и видит ли процесс `VK_GROUP_TOKEN`.

Пересчитать будущие `pending/retry` задачи после изменения окна или дедлайнов:

```bash
.venv/bin/python -m scripts.recalculate_pending_jobs
```

## Запуск через Docker

Создайте `.env`:

```bash
cp .env .env
```

Для mock-режима оставьте `VK_GROUP_TOKEN=` пустым. Для реальной отправки укажите токен сообщества:

```env
VK_GROUP_TOKEN=your_vk_group_token
```

Поднимите сервисы:

```bash
docker compose up -d --build
```

Примените миграции:

```bash
docker compose exec app alembic upgrade head
```

Заполните тестовые данные:

```bash
docker compose exec app python -m scripts.seed
```

API будет доступен на `http://localhost:8000`, документация FastAPI - на `http://localhost:8000/docs`.

## Проверка MVP

Посмотреть созданные задачи:

```bash
curl http://localhost:8000/notification-jobs
```

Создать дедлайн вручную:

```bash
curl -X POST http://localhost:8000/deadlines \
  -H "Content-Type: application/json" \
  -d '{
    "study_group_id": 1,
    "subject": "Физика",
    "title": "Домашнее задание по динамике",
    "description": "Решить задачи 1-15",
    "deadline_at": "2026-05-15T18:00:00+03:00",
    "source": "manual"
  }'
```

После создания дедлайна сервис автоматически создаёт `notification_jobs` для активных правил и активных VK-бесед учебной группы. Дубли запрещены уникальным индексом `deadline_id + vk_chat_id + rule_id`.

## Mock-режим VK

Если переменная окружения, указанная в `vk_communities.token_env_name`, не задана или пустая, `VKSender` не падает и не вызывает VK API. Он пишет сообщение в лог worker’а:

```bash
docker compose logs -f celery_worker
```

## Реальный VK token

1. Создайте токен сообщества VK с правом отправки сообщений.
2. Укажите токен в `.env`, например `VK_GROUP_TOKEN=...`.
3. В базе у сообщества должно быть `token_env_name = "VK_GROUP_TOKEN"`.
4. Убедитесь, что бот добавлен в нужные VK-беседы и имеет право писать сообщения.

## Основные endpoints

- `POST /vk-communities`, `GET /vk-communities`, `GET /vk-communities/{id}`
- `POST /study-groups`, `GET /study-groups`, `GET /study-groups/{id}`
- `POST /vk-chats`, `GET /vk-chats`, `GET /vk-chats/{id}`
- `POST /deadlines`, `GET /deadlines`, `GET /deadlines/{id}`, `PATCH /deadlines/{id}`
- `POST /notification-rules`, `GET /notification-rules`, `PATCH /notification-rules/{id}`
- `GET /notification-jobs`, `GET /notification-jobs/{id}`
