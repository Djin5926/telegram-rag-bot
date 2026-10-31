"""Точка входа: long polling Telegram."""

from __future__ import annotations

import asyncio
import logging

from aiogram.types import BotCommand

from src.bot.wiring import build_bot, build_dispatcher
from src.core.config import get_settings
from src.core.db import dispose_engine
from src.core.logging import setup_logging

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Приветствие и инструкция"),
    BotCommand(command="upload", description="Как загрузить PDF"),
    BotCommand(command="reset", description="Очистить контекст диалога"),
]


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    bot = build_bot(settings)
    dp = build_dispatcher(settings)
    await bot.set_my_commands(COMMANDS)

    logger.info("Бот запущен (long polling)")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
