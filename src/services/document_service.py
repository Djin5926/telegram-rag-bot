"""Документы: сохранение загруженных PDF и CRUD статусов в PostgreSQL."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select

from src.core.config import Settings
from src.core.db import get_session_maker
from src.db.models import Document, User


class DocumentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions = get_session_maker()

    async def save_upload(self, user_id: int, file_name: str, data: bytes) -> Document:
        """Пишет файл в DATA_DIR/user_id/<uuid>.pdf и создаёт запись (status=processing)."""
        await self._ensure_user(user_id)
        document_id = uuid.uuid4()
        folder = self._settings.data_dir / str(user_id)
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{document_id}.pdf"
        file_path.write_bytes(data)

        document = Document(
            id=document_id,
            user_id=user_id,
            file_name=file_name,
            status="processing",
            file_path=str(file_path),
        )
        async with self._sessions() as session:
            session.add(document)
            await session.commit()
            await session.refresh(document)
        return document

    async def get(self, document_id: uuid.UUID) -> Document | None:
        async with self._sessions() as session:
            return await session.get(Document, document_id)

    async def mark_done(self, document_id: uuid.UUID, num_pages: int, num_chunks: int) -> None:
        async with self._sessions() as session:
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = "done"
                document.num_pages = num_pages
                document.num_chunks = num_chunks
                await session.commit()

    async def mark_failed(self, document_id: uuid.UUID, error: str) -> None:
        async with self._sessions() as session:
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = "failed"
                document.error = error[:500]
                await session.commit()

    async def list_done(self, user_id: int) -> list[Document]:
        async with self._sessions() as session:
            result = await session.execute(
                select(Document)
                .where(Document.user_id == user_id, Document.status == "done")
                .order_by(Document.created_at)
            )
            return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: int) -> int:
        """Полная очистка пользователя: записи БД + файлы (для будущих расширений)."""
        async with self._sessions() as session:
            result = await session.execute(delete(Document).where(Document.user_id == user_id))
            await session.commit()
        folder = self._settings.data_dir / str(user_id)
        if folder.exists():
            for pdf in folder.glob("*.pdf"):
                pdf.unlink(missing_ok=True)
        return result.rowcount or 0

    async def _ensure_user(self, user_id: int) -> None:
        async with self._sessions() as session:
            if await session.get(User, user_id) is None:
                session.add(User(id=user_id))
                await session.commit()
