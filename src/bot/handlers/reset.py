"""/reset: очистка контекста диалога (документы остаются)."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.services.history_service import HistoryService

router = Router(name="reset")


@router.message(Command("reset"))
async def cmd_reset(message: Message, history: HistoryService) -> None:
    if message.from_user is None:
        return
    removed = await history.clear(message.from_user.id)
    await message.answer(
        f"🧹 Контекст диалога очищен ({removed} записей).\n"
        "Загруженные документы остались — продолжайте задавать вопросы."
    )
