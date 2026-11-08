"""Eval: прогон вопросов из questions.jsonl через RAG-пайплайн, подсчёт Accuracy.

Использование (нужны запущенные Qdrant и переменные окружения из .env):
    python eval/run_eval.py               # прогон + очистка eval-коллекции
    python eval/run_eval.py --keep        # не удалять коллекцию (для отладки)
    python eval/run_eval.py --no-llm      # только retrieval, без генерации (экономия токенов)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import get_settings  # noqa: E402
from src.core.logging import setup_logging  # noqa: E402
from src.ingestion.chunker import chunk_pages  # noqa: E402
from src.ingestion.embedder import Embedder  # noqa: E402
from src.ingestion.pdf_parser import parse_pdf  # noqa: E402
from src.llm.generator import AnswerGenerator  # noqa: E402
from src.retrieval.qdrant_client import QdrantService  # noqa: E402
from src.retrieval.search import RetrievalService  # noqa: E402

EVAL_DIR = Path(__file__).parent
EVAL_USER_ID = 0  # отдельная eval-коллекция user_0, чтобы не трогать данные реальных пользователей


def load_questions(path: Path) -> list[dict]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _normalize(text: str) -> str:
    """Нижний регистр, ё→е, запятая→точка, только буквы/цифры и .:%-."""
    text = text.lower().replace("ё", "е").replace(",", ".")
    return "".join(ch for ch in text if ch.isalnum() or ch in ".:%")


def is_match(answer: str, expected: str) -> bool:
    """Ответ засчитан, если ожидание содержится в ответе ИЛИ ≥60% слов ожидания найдены."""
    normalized_answer, normalized_expected = _normalize(answer), _normalize(expected)
    if normalized_expected and normalized_expected in normalized_answer:
        return True
    words = [w for w in re.split(r"\W+", expected.lower().replace("ё", "е")) if len(w) > 2]
    if not words:
        return False
    hits = sum(1 for word in words if _normalize(word) in normalized_answer)
    return hits / len(words) >= 0.6


async def ingest_pdfs(pdf_paths: list[Path], embedder: Embedder, qdrant: QdrantService) -> None:
    settings = get_settings()
    for pdf_path in pdf_paths:
        fake_document = SimpleNamespace(file_name=pdf_path.name, id=uuid.uuid4())
        chunks = chunk_pages(
            parse_pdf(pdf_path.read_bytes()),
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        vectors = await embedder.embed_texts([chunk.text for chunk in chunks])
        await qdrant.ensure_user_collection(EVAL_USER_ID)
        await qdrant.upsert_chunks(EVAL_USER_ID, fake_document, chunks, vectors)
        print(f"  проиндексирован {pdf_path.name}: {len(chunks)} чанков")


async def run(use_llm: bool, keep_collection: bool) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    questions = load_questions(EVAL_DIR / "questions.jsonl")
    pdf_paths = sorted({EVAL_DIR / item["pdf"] for item in questions})
    missing = [p for p in pdf_paths if not p.exists()]
    if any("sample.pdf" in p.name for p in missing):
        print("sample.pdf не найден — генерирую (eval/make_sample_pdf.py)…")
        from eval.make_sample_pdf import build_pdf

        build_pdf()
        missing = [p for p in pdf_paths if not p.exists()]
    if missing:
        sys.exit(f"Отсутствуют PDF для eval: {missing}")

    embedder = Embedder(settings)
    qdrant = QdrantService(settings)
    retrieval = RetrievalService(embedder, qdrant, settings)
    generator = AnswerGenerator(settings)

    print(f"Индексация {len(pdf_paths)} документ(ов)…")
    await ingest_pdfs(pdf_paths, embedder, qdrant)

    correct = 0
    print(f"\nПрогон {len(questions)} вопросов…")
    for i, item in enumerate(questions, start=1):
        chunks = await retrieval.search(EVAL_USER_ID, item["question"])
        if use_llm:
            parts = [delta async for delta in generator.stream_answer(item["question"], chunks)]
            answer = "".join(parts).strip()
        else:
            answer = chunks[0].text if chunks else ""
        matched = is_match(answer, item["expected_answer"])
        correct += matched
        mark = "OK  " if matched else "FAIL"
        print(f"{i:2d}. [{mark}] {item['question']}")
        if not matched:
            print(f"      ожидалось: {item['expected_answer']!r}")
            print(f"      получено : {answer[:120]!r}")

    accuracy = correct / len(questions)
    print(f"\nAccuracy: {accuracy:.0%} ({correct}/{len(questions)})")

    if not keep_collection:
        await qdrant.delete_user_collection(EVAL_USER_ID)
        print("Eval-коллекция удалена (--keep, чтобы сохранить)")
    await qdrant.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Оценка качества RAG-пайплайна")
    parser.add_argument("--keep", action="store_true", help="не удалять eval-коллекцию")
    parser.add_argument("--no-llm", action="store_true", help="без генерации (проверка retrieval)")
    args = parser.parse_args()
    asyncio.run(run(use_llm=not args.no_llm, keep_collection=args.keep))
