from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(default="sqlite:///./vk_deadline.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    vk_api_version: str = Field(default="5.199", alias="VK_API_VERSION")
    vk_rate_limit_per_second: int = Field(default=10, alias="VK_RATE_LIMIT_PER_SECOND")
    max_notification_attempts: int = Field(default=5, alias="MAX_NOTIFICATION_ATTEMPTS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
