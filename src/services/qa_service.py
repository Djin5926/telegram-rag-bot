"""Вопрос-ответ: поиск фрагментов, стриминг генерации, история диалога."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from src.core.config import Settings
from src.llm.generator import AnswerGenerator
from src.retrieval.search import RetrievalService, RetrievedChunk
from src.services.history_service import HistoryService


@dataclass
class AskSession:
    """Подготовленный ответ: найденные фрагменты и ленивый стрим генерации."""

    question: str
    chunks: list[RetrievedChunk]
    history: list[tuple[str, str]]
    stream: AsyncIterator[str] = field(repr=False)


class QAService:
    def __init__(
        self,
        retrieval: RetrievalService,
        generator: AnswerGenerator,
        history: HistoryService,
        settings: Settings,
    ) -> None:
        self._retrieval = retrieval
        self._generator = generator
        self._history = history
        self._settings = settings

    async def create_session(self, user_id: int, question: str) -> AskSession:
        history = await self._history.get_recent(user_id, self._settings.history_turns)
        chunks = await self._retrieval.search(user_id, question)
        return AskSession(
            question=question,
            chunks=chunks,
            history=history,
            stream=self._generator.stream_answer(question, chunks, history),
        )

    async def save_turn(self, user_id: int, question: str, answer: str) -> None:
        await self._history.save(user_id, question, answer)
