"""Генерация ответа LLM (OpenAI-совместимый API) со стримингом."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI

from src.core.config import Settings
from src.llm.prompts import build_messages
from src.retrieval.search import RetrievedChunk


class AnswerGenerator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def stream_answer(
        self,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[tuple[str, str]] = (),
    ) -> AsyncIterator[str]:
        """Постепенно выдаёт куски ответа (deltas) из chat.completions stream."""
        stream = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            messages=build_messages(question, chunks, history),
            stream=True,
            temperature=0.2,
            max_tokens=800,
        )
        async for event in stream:
            if event.choices and event.choices[0].delta.content:
                yield event.choices[0].delta.content
