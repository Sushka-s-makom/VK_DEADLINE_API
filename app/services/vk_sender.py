from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import NotificationJob, VKChat, VKCommunity
from app.services.message_composer import compose_deadline_message

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(".env"))


@dataclass
class VKSendResult:
    ok: bool
    message_id: int | None = None
    error: str | None = None
    mock: bool = False
    temporary: bool = True


class VKRateLimiter:
    def __init__(self, per_second: int) -> None:
        self.min_interval = 1 / max(per_second, 1)
        self._last_sent_at = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_sent_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_sent_at = time.monotonic()


class VKSender:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rate_limiter = VKRateLimiter(self.settings.vk_rate_limit_per_second)

    def send_job(self, job: NotificationJob) -> VKSendResult:
        composed = self.render_message(job)
        return self.send_message(job.vk_chat, composed.text, attachment=composed.attachment)

    def send_message(self, chat: VKChat, message: str, attachment: str | None = None) -> VKSendResult:
        community: VKCommunity = chat.community
        token = os.getenv(community.token_env_name)

        logger.info("VK send attempt community=%s peer_id=%s", community.id, chat.peer_id)
        if not token:
            logger.info("VK mock send token_env_name=%s peer_id=%s message=%s", community.token_env_name, chat.peer_id, message)
            return VKSendResult(ok=True, message_id=None, mock=True)

        self.rate_limiter.wait()
        try:
            response = requests.post(
                "https://api.vk.com/method/messages.send",
                data={
                    "access_token": token,
                    "v": self.settings.vk_api_version,
                    "peer_id": chat.peer_id,
                    "random_id": random.randint(1, 2_147_483_647),
                    "message": message,
                    "attachment": attachment or "",
                },
                timeout=10,
            )
            payload = response.json()
        except Exception as exc:
            logger.exception("VK send request failed")
            return VKSendResult(ok=False, error=str(exc), temporary=True)

        if "response" in payload:
            logger.info("VK send success peer_id=%s message_id=%s", chat.peer_id, payload["response"])
            return VKSendResult(ok=True, message_id=int(payload["response"]))

        error = payload.get("error", {})
        error_message = error.get("error_msg", str(payload))
        logger.warning("VK send failed peer_id=%s error=%s", chat.peer_id, error_message)
        return VKSendResult(ok=False, error=error_message, temporary=True)

    def render_message(self, job: NotificationJob):
        with SessionLocal() as db:
            deadline = db.merge(job.deadline)
            return compose_deadline_message(db, deadline)
