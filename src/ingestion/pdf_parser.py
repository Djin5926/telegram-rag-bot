"""Парсинг PDF через PyMuPDF: текст по страницам + блоки с координатами.

Координаты блоков (bbox) сохраняются для последующей подсветки источника,
но основной пайплайн работает с текстом страницы.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf as fitz  # PyMuPDF


class PdfParseError(Exception):
    """Ошибка разбора PDF (битый файл, пароль, пустой документ)."""


@dataclass(frozen=True)
class TextBlock:
    text: str
    # (x0, y0, x1, y1) в координатах страницы
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class ParsedPage:
    number: int  # 1-based, как принято в цитатах «стр. N»
    text: str
    blocks: tuple[TextBlock, ...]


def parse_pdf(data: bytes) -> list[ParsedPage]:
    """Извлекает текст всех страниц. Бросает PdfParseError на проблемных файлах."""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfParseError(f"не удалось открыть PDF: {exc}") from exc

    with doc:
        if doc.needs_pass:
            raise PdfParseError("PDF защищён паролем")
        if doc.page_count == 0:
            raise PdfParseError("PDF не содержит страниц")
        return [_parse_page(number, page) for number, page in enumerate(doc, start=1)]


def _parse_page(number: int, page: fitz.Page) -> ParsedPage:
    # sort=True — блоки в порядке чтения; item[6] == 0 — текстовый блок, не картинка
    raw = page.get_text("blocks", sort=True)
    blocks = tuple(
        # \xad (soft hyphen) — артефакт вёрстки; восстанавливаем обычный дефис
        TextBlock(
            text=item[4].strip().replace("\xad", "-"),
            bbox=(item[0], item[1], item[2], item[3]),
        )
        for item in raw
        if item[6] == 0 and item[4].strip()
    )
    return ParsedPage(number=number, text="\n\n".join(b.text for b in blocks), blocks=blocks)
