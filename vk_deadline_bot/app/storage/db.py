from __future__ import annotations

import asyncio
from typing import Optional

import asyncpg

from vk_deadline_bot.app.config import AppConfig, get_config


_pool: Optional[asyncpg.pool.Pool] = None
_pool_lock = asyncio.Lock()


async def create_pool(config: Optional[AppConfig] = None) -> asyncpg.pool.Pool:
    """Создаёт и кэширует пул подключений к PostgreSQL."""
    global _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        if config is None:
            config = get_config()

        db = config.db

        connect_kwargs = {}
        if db.dsn:
            connect_kwargs["dsn"] = db.dsn
        else:
            connect_kwargs.update(
                host=db.host,
                port=db.port,
                database=db.database,
                user=db.user,
                password=db.password,
            )

        _pool = await asyncpg.create_pool(**connect_kwargs)
        return _pool


def get_pool() -> asyncpg.pool.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call create_pool() first.")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


__all__ = ["create_pool", "get_pool", "close_pool"]

