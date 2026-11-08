"""Клиент Qdrant. Изоляция данных: один пользователь — одна коллекция."""

from __future__ import annotations

import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.core.config import Settings
from src.db.models import Document
from src.ingestion.chunker import Chunk


class QdrantService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )

    @staticmethod
    def collection_name(user_id: int) -> str:
        return f"user_{user_id}"

    async def ensure_user_collection(self, user_id: int) -> str:
        """Создаёт коллекцию пользователя, если её ещё нет."""
        name = self.collection_name(user_id)
        if not await self._client.collection_exists(name):
            await self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self._settings.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
        return name

    async def upsert_chunks(
        self,
        user_id: int,
        document: Document,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"chunks ({len(chunks)}) и vectors ({len(vectors)}) разной длины")
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "file_name": document.file_name,
                    "document_id": str(document.id),
                    "user_id": user_id,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self._client.upsert(
            collection_name=self.collection_name(user_id),
            points=points,
            wait=True,
        )

    async def search(self, user_id: int, query_vector: list[float], top_k: int) -> list:
        """Top-K ближайших чанков из коллекции пользователя."""
        response = await self._client.query_points(
            collection_name=self.collection_name(user_id),
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return list(response.points)

    async def delete_user_collection(self, user_id: int) -> None:
        name = self.collection_name(user_id)
        if await self._client.collection_exists(name):
            await self._client.delete_collection(name)

    async def close(self) -> None:
        await self._client.close()
