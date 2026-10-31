"""Настройка логирования (stdlib logging, без внешних зависимостей)."""

import logging

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Сторонние библиотеки слишком болтливы на DEBUG
    for noisy in ("aiogram.event", "httpx", "openai", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
