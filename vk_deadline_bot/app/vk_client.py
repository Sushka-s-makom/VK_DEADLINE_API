from __future__ import annotations

from typing import Any, Dict, Optional

from vkbottle import API


class VkClient:
    """Тонкая обёртка над VK API для отправки сообщений."""

    def __init__(self, api: API) -> None:
        self._api = api

    async def send_message(
        self,
        peer_id: int,
        text: str,
        random_id: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Отправка сообщения в беседу/личку.

        В VK API random_id должен быть уникальным для предотвращения дублей.
        В MVP можно передавать 0, если вы сами контролируете антидубли в БД.
        """
        payload: Dict[str, Any] = {"peer_id": peer_id, "message": text, "random_id": random_id}
        payload.update(kwargs)
        return await self._api.messages.send(**payload)


__all__ = ["VkClient"]

