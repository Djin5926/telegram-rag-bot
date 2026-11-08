"""Приём PDF-документов: /upload и хендлер вложений.

Обработка (парсинг, чанкинг, эмбеддинги) уходит в фоновую задачу,
чтобы бот не блокировал чат на время пайплайна.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.config import Settings
from src.services.document_service import DocumentService
from src.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)
router = Router(name="documents")

# ссылки на фоновые задачи, чтобы их не собрал GC во время выполнения
_background_tasks: set[asyncio.Task] = set()


def _is_pdf(file_name: str | None, mime_type: str | None) -> bool:
    if mime_type == "application/pdf":
        return True
    return bool(file_name and file_name.lower().endswith(".pdf"))


@router.message(Command("upload"))
async def cmd_upload(message: Message, settings: Settings) -> None:
    await message.answer(
        "📎 Прикрепи PDF-файл к сообщению (кнопка скрепки), "
        f"до {settings.max_pdf_size_mb} МБ.\n\n"
        "Можно загрузить несколько документов и спрашивать сразу по всем, "
        "например: «Сравни условия в договоре_1.pdf и договоре_2.pdf»."
    )


@router.message(F.document)
async def handle_document(
    message: Message,
    bot: Bot,
    settings: Settings,
    documents: DocumentService,
    ingestion: IngestionService,
) -> None:
    if message.from_user is None or message.document is None:
        return

    tg_doc = message.document
    if not _is_pdf(tg_doc.file_name, tg_doc.mime_type):
        await message.answer("⚠️ Пока принимаю только PDF-файлы.")
        return
    if tg_doc.file_size and tg_doc.file_size > settings.max_pdf_size_bytes:
        await message.answer(
            f"⚠️ Файл больше {settings.max_pdf_size_mb} МБ. "
            "Сожмите документ или разбейте его на части."
        )
        return

    status = await message.answer(f"⏳ Загружаю и обрабатываю «{tg_doc.file_name}»…")
    buffer = BytesIO()
    await bot.download(tg_doc, destination=buffer)

    try:
        document = await documents.save_upload(
            message.from_user.id, tg_doc.file_name or "document.pdf", buffer.getvalue()
        )
    except Exception:
        logger.exception("не удалось сохранить загрузку")
        await status.edit_text("⚠️ Не удалось сохранить файл. Попробуйте ещё раз.")
        return

    file_name = tg_doc.file_name or "document.pdf"
    task = asyncio.create_task(
        _process_and_report(
            bot, status.chat.id, status.message_id, ingestion, document.id, file_name
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _process_and_report(
    bot: Bot,
    chat_id: int,
    status_message_id: int,
    ingestion: IngestionService,
    document_id: uuid.UUID,
    file_name: str,
) -> None:
    try:
        num_pages, num_chunks = await ingestion.process_document(document_id)
    except Exception as exc:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_message_id,
            text=f"⚠️ Не удалось обработать «{file_name}»: {exc}",
        )
        return
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=status_message_id,
        text=(
            f"✅ «{file_name}» обработан: {num_pages} стр., {num_chunks} фрагментов.\n"
            "Теперь задавай вопросы по документу!"
        ),
    )
