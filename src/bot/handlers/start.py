"""/start и /help: приветствие и краткая инструкция."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")

WELCOME = (
    "👋 Привет! Я бот, который отвечает на вопросы по твоим PDF-документам.\n\n"
    "<b>Как пользоваться</b>\n"
    "1. Прикрепи PDF к сообщению (скрепка 📎) — я разберу его на фрагменты и запомню. "
    "Можно загрузить несколько документов.\n"
    "2. Просто напиши вопрос — я найду релевантные места и отвечу с указанием источника.\n\n"
    "<b>Команды</b>\n"
    "/upload — как загрузить документ\n"
    "/reset — очистить контекст диалога\n\n"
    "Я отвечаю только по содержимому твоих документов и честно скажу, "
    "если ответа в них нет."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME)
