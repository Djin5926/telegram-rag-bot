"""Пайплайн загрузки документа: parse -> chunk -> embed -> Qdrant -> метаданные."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from src.core.config import Settings
from src.ingestion.chunker import Chunk, chunk_pages
from src.ingestion.embedder import Embedder
from src.ingestion.pdf_parser import PdfParseError, parse_pdf
from src.retrieval.qdrant_client import QdrantService
from src.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        embedder: Embedder,
        qdrant: QdrantService,
        documents: DocumentService,
        settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._qdrant = qdrant
        self._documents = documents
        self._settings = settings

    async def process_document(self, document_id: uuid.UUID) -> tuple[int, int]:
        """Полный цикл обработки. Возвращает (число страниц, число чанков).

        Статусы в БД обновляет сам (done/failed); при ошибке пробрасывает исключение.
        """
        document = await self._documents.get(document_id)
        if document is None:
            raise LookupError(f"документ {document_id} не найден")

        try:
            data = Path(document.file_path).read_bytes()
            pages = parse_pdf(data)
            chunks = self._build_chunks(pages)
            vectors = await self._embedder.embed_texts([chunk.text for chunk in chunks])
            await self._qdrant.ensure_user_collection(document.user_id)
            await self._qdrant.upsert_chunks(document.user_id, document, chunks, vectors)
        except Exception as exc:
            logger.exception("ошибка обработки документа %s", document_id)
            await self._documents.mark_failed(document_id, str(exc))
            raise

        await self._documents.mark_done(document_id, num_pages=len(pages), num_chunks=len(chunks))
        return len(pages), len(chunks)

    def _build_chunks(self, pages: list) -> list[Chunk]:
        chunks = chunk_pages(
            pages,
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        if not chunks:
            raise PdfParseError(
                "в документе не найден текстовый слой "
                "(возможно, это сканы без распознанного текста)"
            )
        return chunks
