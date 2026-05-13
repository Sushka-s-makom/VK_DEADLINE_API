from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    dsn: str | None = None


@dataclass
class GoogleConfig:
    credentials_file: str | None = None
    project_id: str | None = None


@dataclass
class AppConfig:
    vk_bot_token: str
    db: DatabaseConfig
    google: GoogleConfig


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Загружает конфигурацию приложения из переменных окружения."""
    vk_bot_token = os.environ.get("VK_BOT_TOKEN")
    if not vk_bot_token:
        raise RuntimeError("VK_BOT_TOKEN is not set")

    db = DatabaseConfig(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        database=os.environ.get("PG_DB", "vk_deadline"),
        user=os.environ.get("PG_USER", "vk_deadline"),
        password=os.environ.get("PG_PASSWORD", "vk_deadline"),
        dsn=os.environ.get("PG_DSN") or None,
    )

    google = GoogleConfig(
        credentials_file=os.environ.get("GOOGLE_CREDENTIALS_FILE"),
        project_id=os.environ.get("GOOGLE_PROJECT_ID"),
    )

    return AppConfig(
        vk_bot_token=vk_bot_token,
        db=db,
        google=google,
    )


__all__ = ["AppConfig", "DatabaseConfig", "GoogleConfig", "get_config"]

