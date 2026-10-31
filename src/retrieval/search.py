"""Поиск релевантных фрагментов по эмбеддингу вопроса."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import Settings
from src.ingestion.embedder import Embedder
from src.retrieval.qdrant_client import QdrantService


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    page_number: int
    file_name: str
    document_id: str
    score: float


class RetrievalService:
    def __init__(self, embedder: Embedder, qdrant: QdrantService, settings: Settings) -> None:
        self._embedder = embedder
        self._qdrant = qdrant
        self._settings = settings

    async def search(
        self, user_id: int, query: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        top_k = top_k or self._settings.top_k
        query_vector = (await self._embedder.embed_texts([query]))[0]
        points = await self._qdrant.search(user_id, query_vector, top_k)
        return [
            RetrievedChunk(
                text=point.payload.get("text", ""),
                page_number=int(point.payload.get("page_number", 0)),
                file_name=str(point.payload.get("file_name", "?")),
                document_id=str(point.payload.get("document_id", "")),
                score=point.score,
            )
            for point in points
        ]

    @staticmethod
    def format_sources(chunks: list[RetrievedChunk]) -> str:
        """Строка цитирования: уникальные пары «файл, страница» в порядке релевантности."""
        unique: list[tuple[str, int]] = []
        for chunk in chunks:
            pair = (chunk.file_name, chunk.page_number)
            if pair not in unique:
                unique.append(pair)
        if not unique:
            return ""
        if len(unique) == 1:
            file_name, page = unique[0]
            return f"Источник: {file_name}, стр. {page}"
        joined = "; ".join(f"{file_name}, стр. {page}" for file_name, page in unique)
        return f"Источники: {joined}"
