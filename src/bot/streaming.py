"""Постепенное редактирование сообщения Telegram при стриминге ответа LLM.

Telegram ограничивает частоту editMessageText (~1 раз в секунду на чат),
поэтому правки отправляются не чаще _EDIT_INTERVAL; финальная — всегда.
"""

from __future__ import annotations

import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

_EDIT_INTERVAL = 1.2  # сек
_MAX_LEN = 4000  # лимит Telegram 4096 — оставляем запас


class TelegramStreamEditor:
    def __init__(self, bot: Bot, chat_id: int, message_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id
        self._last_edit = 0.0
        self._last_text: str | None = None

    async def update(self, text: str) -> None:
        """Промежуточное обновление (пропускается, если слишком рано после прошлого)."""
        if time.monotonic() - self._last_edit < _EDIT_INTERVAL:
            return
        await self._edit(text)

    async def finalize(self, text: str) -> None:
        """Финальная правка — выполняется всегда, независимо от троттлинга."""
        await self._edit(text)

    async def _edit(self, text: str) -> None:
        text = _truncate(text)
        if text == self._last_text:
            return
        try:
            await self._bot.edit_message_text(
                chat_id=self._chat_id,
                message_id=self._message_id,
                text=text,
            )
        except TelegramBadRequest as exc:
            # «message is not modified» — текст не успел измениться, это норма
            if "message is not modified" not in str(exc).lower():
                raise
        self._last_text = text
        self._last_edit = time.monotonic()


def _truncate(text: str) -> str:
    """Обрезает длинный ответ, сохраняя начало и конец (лимит Telegram 4096)."""
    if len(text) <= _MAX_LEN:
        return text
    head, tail = text[:3000], text[-900:]
    return f"{head}\n\n[…] ответ сокращён […] \n\n{tail}"
