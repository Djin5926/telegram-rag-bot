"""Промпты: строгий anti-hallucination системный промпт и сборка сообщений."""

from __future__ import annotations

from collections.abc import Sequence

from src.retrieval.search import RetrievedChunk

SYSTEM_PROMPT = """Ты — эксперт по анализу документов. Твоя задача — отвечать на вопросы пользователя, используя ТОЛЬКО предоставленный контекст.
Правила:
1. Отвечай кратко, по делу, на русском языке.
2. Если в контексте есть ответ — обязательно процитируй его.
3. Если ответа в контексте нет, скажи: "В предоставленных документах ответа нет".
4. Не выдумывай факты и не используй свои общие знания."""
# 👆 Вот здесь я добавил закрывающие три кавычки!


def build_messages(
    question: str,
    chunks: Sequence[RetrievedChunk],
    history: Sequence[tuple[str, str]] = (),
) -> list[dict[str, str]]:
    """Сообщения для chat.completions: система + последние реплики диалога + вопрос с контекстом."""
    context_blocks = [
        f"[{i}] ({chunk.file_name}, стр. {chunk.page_number})\n{chunk.text}"
        for i, chunk in enumerate(chunks, start=1)
    ]
    user_content = (
        "Контекст — фрагменты документов:\n\n"
        + "\n\n".join(context_blocks)
        + f"\n\nВопрос: {question}"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for prev_question, prev_answer in history:
        messages.append({"role": "user", "content": prev_question})
        messages.append({"role": "assistant", "content": prev_answer})
    messages.append({"role": "user", "content": user_content})
    return messages