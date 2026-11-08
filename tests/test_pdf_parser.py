"""Unit-тесты парсера PDF (src/ingestion/pdf_parser.py) и подсветки (highlighter.py)."""

import pymupdf as fitz
import pytest

from src.ingestion.highlighter import render_page_with_highlight
from src.ingestion.pdf_parser import PdfParseError, parse_pdf


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Service contract No. 42")
    page.insert_text((72, 100), "SLA availability is 99.9 percent monthly.")
    second = doc.new_page()
    second.insert_text((72, 72), "Page two: penalty of 10 percent.")
    data = doc.tobytes()
    doc.close()
    return data


def test_parse_returns_all_pages(sample_pdf_bytes):
    pages = parse_pdf(sample_pdf_bytes)
    assert len(pages) == 2
    assert [page.number for page in pages] == [1, 2]


def test_page_text_contains_inserted_lines(sample_pdf_bytes):
    pages = parse_pdf(sample_pdf_bytes)
    assert "Service contract" in pages[0].text
    assert "99.9" in pages[0].text
    assert "penalty" in pages[1].text


def test_blocks_have_bboxes(sample_pdf_bytes):
    pages = parse_pdf(sample_pdf_bytes)
    blocks = pages[0].blocks
    assert blocks, "ожидались текстовые блоки"
    for block in blocks:
        x0, y0, x1, y1 = block.bbox
        assert x1 > x0 and y1 > y0


def test_page_text_is_join_of_blocks(sample_pdf_bytes):
    page = parse_pdf(sample_pdf_bytes)[0]
    assert page.text == "\n\n".join(block.text for block in page.blocks)


def test_broken_pdf_raises_pdfparseerror():
    with pytest.raises(PdfParseError):
        parse_pdf(b"this is definitely not a pdf file")


def test_highlight_renders_png(sample_pdf_bytes):
    image = render_page_with_highlight(sample_pdf_bytes, 1, "SLA availability is 99.9")
    assert image[:8] == b"\x89PNG\r\n\x1a\n"


def test_highlight_page_out_of_range_raises(sample_pdf_bytes):
    with pytest.raises(ValueError):
        render_page_with_highlight(sample_pdf_bytes, 5, "anything")
