"""Сборка бота: конструирование сервисов и внедрение их в хендлеры (DI через Dispatcher)."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импортируем модули хендлеров (роутеры)
from src.bot.handlers import documents, questions, reset, start
from src.core.config import Settings
from src.core.db import init_engine
from src.ingestion.embedder import Embedder
from src.llm.generator import AnswerGenerator
from src.retrieval.qdrant_client import QdrantService
from src.retrieval.search import RetrievalService
from src.services.document_service import DocumentService
from src.services.history_service import HistoryService
from src.services.ingestion_service import IngestionService
from src.services.qa_service import QAService


def build_bot(settings: Settings) -> Bot:
    return Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def build_dispatcher(settings: Settings) -> Dispatcher:
    init_engine(settings)

    # клиенты
    embedder = Embedder(settings)
    qdrant = QdrantService(settings)

    # сервисы (переименовали переменную, чтобы не конфликтовала с модулем handlers)
    document_service = DocumentService(settings)
    history = HistoryService()
    ingestion = IngestionService(embedder, qdrant, document_service, settings)
    retrieval = RetrievalService(embedder, qdrant, settings)
    generator = AnswerGenerator(settings)
    qa = QAService(retrieval, generator, history, settings)

    dp = Dispatcher()
    
    # Передаем сервисы в контекст диспетчера (они будут доступны в хендлерах)
    dp["settings"] = settings
    dp["documents"] = document_service
    dp["history"] = history
    dp["ingestion"] = ingestion
    dp["qa"] = qa
    
    # Подключаем роутеры (теперь documents ссылается на модуль из handlers)
    dp.include_routers(start.router, documents.router, questions.router, reset.router)
    return dp