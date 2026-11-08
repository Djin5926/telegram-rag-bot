"""История диалога: последние пары вопрос-ответ для контекста LLM, очистка по /reset."""

from __future__ import annotations

from sqlalchemy import delete, select

from src.core.db import get_session_maker
from src.db.models import Message


class HistoryService:
    def __init__(self) -> None:
        self._sessions = get_session_maker()

    async def get_recent(self, user_id: int, limit: int) -> list[tuple[str, str]]:
        """Последние `limit` пар (вопрос, ответ) в хронологическом порядке."""
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(Message)
                    .where(Message.user_id == user_id)
                    .order_by(Message.created_at.desc(), Message.id.desc())
                    .limit(limit)
                )
            ).scalars().all()
        return [(message.question, message.answer) for message in reversed(rows)]

    async def save(self, user_id: int, question: str, answer: str) -> None:
        async with self._sessions() as session:
            session.add(Message(user_id=user_id, question=question, answer=answer))
            await session.commit()

    async def clear(self, user_id: int) -> int:
        """Удаляет историю диалога пользователя. Возвращает число удалённых записей."""
        async with self._sessions() as session:
            result = await session.execute(delete(Message).where(Message.user_id == user_id))
            await session.commit()
        return result.rowcount or 0
