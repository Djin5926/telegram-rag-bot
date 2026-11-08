"""Чанкинг: разбивка текста страниц на куски ≤ chunk_size токенов с перекрытием.

Стратегия:
1. Текст страницы делится на параграфы (пустые строки).
2. Параграфы жадно упаковываются в чанки; при переполнении чанк закрывается.
3. Следующий чанк начинается с «хвоста» предыдущего (≤ chunk_overlap токенов),
   чтобы фраза на границе не теряла контекст.
4. Слишком длинный параграф режется по словам.

Чанки не пересекают границы страниц — цитата всегда указывает конкретную страницу.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from src.ingestion.pdf_parser import ParsedPage

TokenCounter = Callable[[str], int]

_counter: TokenCounter | None = None


def _get_token_counter() -> TokenCounter:
    """Счётчик токенов: tiktoken (cl100k_base) с fallback на приближение по символам.

    Fallback нужен, если файлы кодировок недоступны (офлайн-сборка):
    для русских текстов ~3 символа на токен.
    """
    global _counter
    if _counter is None:
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            _counter = lambda text: len(enc.encode(text))  # noqa: E731
        except Exception:
            _counter = lambda text: max(1, (len(text) + 2) // 3)  # noqa: E731
    return _counter


@dataclass(frozen=True)
class Chunk:
    text: str
    page_number: int
    n_tokens: int


def chunk_pages(
    pages: list[ParsedPage],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    count_tokens: TokenCounter | None = None,
) -> list[Chunk]:
    """Разбивает страницы на чанки. `count_tokens` инжектится для тестов."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap должен быть меньше chunk_size")
    count = count_tokens or _get_token_counter()

    chunks: list[Chunk] = []
    for page in pages:
        units = _page_units(page.text, chunk_size, count)
        if not units:
            continue

        current: list[str] = []
        current_len = 0
        for unit in units:
            unit_len = count(unit)
            if current and current_len + unit_len > chunk_size:
                chunk_text = "\n\n".join(current)
                chunks.append(
                    Chunk(text=chunk_text, page_number=page.number, n_tokens=count(chunk_text))
                )
                # хвост предыдущего чанка — начало следующего
                tail = _tail_within_budget(chunk_text, chunk_overlap, count)
                if tail and count(tail) + unit_len <= chunk_size:
                    current = [tail]
                    current_len = count(tail)
                else:
                    current = []
                    current_len = 0
            current.append(unit)
            current_len += unit_len

        if current:
            chunk_text = "\n\n".join(current)
            chunks.append(
                Chunk(text=chunk_text, page_number=page.number, n_tokens=count(chunk_text))
            )
    return chunks


def _page_units(text: str, chunk_size: int, count: TokenCounter) -> list[str]:
    """Атомы упаковки: параграфы ≤ chunk_size (длинные порезаны по словам)."""
    units: list[str] = []
    for paragraph in _split_paragraphs(text):
        if count(paragraph) <= chunk_size:
            units.append(paragraph)
        else:
            units.extend(_split_by_words(paragraph, chunk_size, count))
    return units


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_by_words(text: str, chunk_size: int, count: TokenCounter) -> list[str]:
    """Режет фрагмент по границам слов на части ≤ chunk_size токенов."""
    pieces: list[str] = []
    current: list[str] = []
    for word in text.split():
        current.append(word)
        if len(current) > 1 and count(" ".join(current)) > chunk_size:
            current.pop()
            pieces.append(" ".join(current))
            current = [word]
    if current:
        pieces.append(" ".join(current))
    return pieces


def _tail_within_budget(text: str, budget: int, count: TokenCounter) -> str:
    """Последние слова text суммарной «стоимостью» ≤ budget токенов."""
    tail: list[str] = []
    for word in reversed(text.split()):
        candidate = [word, *tail]
        if count(" ".join(candidate)) > budget:
            break
        tail = candidate
    return " ".join(tail)
