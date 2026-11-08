"""Векторизация текстов через локальный Ollama (OpenAI-совместимый API)."""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from src.core.config import Settings


class Embedder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        
        # 👇 Создаем HTTP-клиент с trust_env=False. 
        # Это заставит его игнорировать глобальные переменные прокси 
        # и ходить напрямую к внутреннему сервису ollama.
        http_client = httpx.AsyncClient(trust_env=False)
        
        # ИСПОЛЬЗУЕМ НАСТРОЙКИ ДЛЯ ЭМБЕДДИНГОВ (Ollama), а не для LLM (DeepSeek)
        self._client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            http_client=http_client,  # 👈 Передаем наш кастомный клиент
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Эмбеддинги для списка текстов; порядок результата совпадает с входом."""
        if not texts:
            return []
        vectors: list[list[float]] = []
        batch_size = self._settings.embedding_batch_size
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = await self._client.embeddings.create(
                model=self._settings.embedding_model,
                input=batch,
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
        return vectors