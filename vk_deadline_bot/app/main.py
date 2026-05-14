from __future__ import annotations

import logging

from vkbottle.bot import Bot, Message

from vk_deadline_bot.app.config import get_config
from vk_deadline_bot.app.scheduler import setup_scheduler, get_scheduler
from vk_deadline_bot.app.storage.db import close_pool, create_pool
from vk_deadline_bot.app.storage.repositories import CoursesRepository, GroupsRepository


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


config = get_config()
bot = Bot(token=config.vk_bot_token)


@bot.on.message(text="/ping")
async def ping_handler(message: Message) -> None:
    await message.answer("pong")


@bot.on.message(text="/set_course <code>")
async def set_course_handler(message: Message, code: str) -> None:
    """Привязка беседы к курсу по его vk_code."""
    courses_repo = CoursesRepository()
    groups_repo = GroupsRepository()

    course = await courses_repo.get_by_vk_code(code)
    if course is None:
        await message.answer(f"Курс с кодом '{code}' не найден.")
        return

    peer_id = message.peer_id
    await groups_repo.upsert_group(peer_id=peer_id, course_id=course.id, title=message.peer_id)
    await message.answer(f"Беседа привязана к курсу '{course.name}' (код: {course.vk_code}).")


async def on_startup() -> None:
    logger.info("Starting VK Deadline Bot...")
    await create_pool(config)
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started.")


async def on_shutdown() -> None:
    logger.info("Shutting down VK Deadline Bot...")
    scheduler = get_scheduler()
    scheduler.shutdown(wait=False)
    await close_pool()
    logger.info("Shutdown complete.")


def run() -> None:
    bot.loop_wrapper.on_startup.append(on_startup)
    bot.loop_wrapper.on_shutdown.append(on_shutdown)
    bot.run_forever()


if __name__ == "__main__":
    run()

