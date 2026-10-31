"""«Вау»-фича: рендер страницы PDF в PNG с жёлтой подсветкой найденного фрагмента.

PyMuPDF умеет добавлять аннотацию-маркер (как выделение текста вручную) —
визуально это и есть полупрозрачный жёлтый прямоугольник поверх текста.
"""

from __future__ import annotations

import pymupdf as fitz  # PyMuPDF

# Для уникальной привязки к странице хватает начала фрагмента;
# длинная строка может не совпасть из-за переносов строк в PDF
_SNIPPET_LIMIT = 200
_HIGHLIGHT_COLOR = (1.0, 0.85, 0.1)  # жёлтый


def render_page_with_highlight(
    pdf_bytes: bytes, page_number: int, snippet: str, zoom: float = 2.0
) -> bytes:
    """PNG-картинка страницы `page_number` (1-based) с подсветкой `snippet`.

    Если фрагмент не находится поиском (текст исказился при извлечении),
    страница возвращается без подсветки — фича не должна ломать ответ.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not 1 <= page_number <= doc.page_count:
            raise ValueError(f"страница {page_number} вне диапазона 1..{doc.page_count}")
        page = doc[page_number - 1]

        rects = _find_snippet_rects(page, snippet)
        if rects:
            annot = page.add_highlight_annot(rects)
            if annot is not None:
                annot.set_colors(stroke=_HIGHLIGHT_COLOR)
                annot.update()

        # annots=True — иначе pixmap не отрисует только что добавленную подсветку
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), annots=True)
        return pixmap.tobytes("png")


def _find_snippet_rects(page: fitz.Page, snippet: str) -> list[fitz.Rect]:
    """Прямоугольники вхождений фрагмента: сперва полный сниппет, затем по первым словам."""
    needle = snippet[:_SNIPPET_LIMIT].strip()
    if not needle:
        return []
    rects = page.search_for(needle)
    if rects:
        return rects

    words = needle.split()
    for take in range(min(len(words), 20), 2, -1):
        rects = page.search_for(" ".join(words[:take]))
        if rects:
            return rects
    return []
