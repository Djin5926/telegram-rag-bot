"""Ответы на текстовые вопросы: retrieval -> стриминг ответа -> источники -> подсветка."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, Message

from src.bot.streaming import TelegramStreamEditor
from src.ingestion.highlighter import render_page_with_highlight
from src.retrieval.search import RetrievalService, RetrievedChunk
from src.services.document_service import DocumentService
from src.services.qa_service import QAService

logger = logging.getLogger(__name__)
router = Router(name="questions")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_question(
    message: Message,
    bot: Bot,
    qa: QAService,
    documents: DocumentService,
) -> None:
    if message.from_user is None or not message.text:
        return
    question = message.text.strip()
    if not question:
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    session = await qa.create_session(message.from_user.id, question)

    if not session.chunks:
        await message.answer(
            "🤷 Не нашёл релевантных фрагментов. Загрузите PDF (см. /upload) "
            "и убедитесь, что документ обработан, затем спросите ещё раз."
        )
        return

    placeholder = await message.answer("…")
    editor = TelegramStreamEditor(bot, message.chat.id, placeholder.message_id)

    parts: list[str] = []
    try:
        async for delta in session.stream:
            parts.append(delta)
            await editor.update("".join(parts))
    except Exception:
        logger.exception("генерация ответа не удалась")
        await editor.finalize("⚠️ Не удалось получить ответ. Попробуйте позже.")
        return

    answer = "".join(parts).strip()
    sources = RetrievalService.format_sources(session.chunks)
    await editor.finalize(f"{answer}\n\n{sources}" if sources else answer)
    await qa.save_turn(message.from_user.id, question, answer)

    await _send_highlight(message, documents, session.chunks[0])


async def _send_highlight(
    message: Message, documents: DocumentService, best: RetrievedChunk
) -> None:
    """«Вау»-фича: картинка страницы с подсветкой найденного фрагмента.

    Ошибка подсветки не должна ломать диалог — просто логируем.
    """
    try:
        document = await documents.get(uuid.UUID(best.document_id))
        if document is None:
            return
        image = render_page_with_highlight(
            Path(document.file_path).read_bytes(), best.page_number, best.text
        )
        await message.answer_photo(
            photo=BufferedInputFile(image, filename="source.png"),
            caption=f"🔦 {best.file_name}, стр. {best.page_number}",
        )
    except Exception:
        logger.warning("не удалось отправить подсветку источника", exc_info=True)
