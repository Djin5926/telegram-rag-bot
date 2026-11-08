"""Unit-тесты чанкера (src/ingestion/chunker.py)."""

import pytest

from src.ingestion.chunker import _tail_within_budget, chunk_pages
from src.ingestion.pdf_parser import ParsedPage


def make_page(number: int, text: str) -> ParsedPage:
    return ParsedPage(number=number, text=text, blocks=())


def paragraph(prefix: str, words: int) -> str:
    return " ".join(f"{prefix}w{i}" for i in range(words))


def test_empty_input_gives_no_chunks(word_counter):
    assert chunk_pages([], count_tokens=word_counter) == []


def test_page_without_text_is_skipped(word_counter):
    pages = [make_page(1, ""), make_page(2, "   \n\n  "), make_page(3, "осмысленный текст")]
    chunks = chunk_pages(pages, count_tokens=word_counter)
    assert len(chunks) == 1
    assert chunks[0].page_number == 3


def test_small_page_is_single_chunk(word_counter):
    text = "первый абзац\n\nвторой абзац"
    chunks = chunk_pages([make_page(7, text)], count_tokens=word_counter)
    assert len(chunks) == 1
    assert chunks[0].page_number == 7
    assert "первый абзац" in chunks[0].text
    assert "второй абзац" in chunks[0].text


def test_chunks_do_not_exceed_size(word_counter):
    text = "\n\n".join(paragraph(f"p{i}", 100) for i in range(6))  # 6 абзацев по 100 слов
    chunks = chunk_pages(
        [make_page(1, text)],
        chunk_size=250,
        chunk_overlap=30,
        count_tokens=word_counter,
    )
    assert len(chunks) > 1
    assert all(chunk.n_tokens <= 250 for chunk in chunks)
    # каждый чанк целиком укладывается в лимит и по фактическому тексту
    assert all(word_counter(chunk.text) <= 250 for chunk in chunks)


def test_overlap_connects_consecutive_chunks(word_counter):
    text = "\n\n".join(paragraph(f"p{i}", 100) for i in range(4))
    chunks = chunk_pages(
        [make_page(1, text)],
        chunk_size=250,
        chunk_overlap=30,
        count_tokens=word_counter,
    )
    first_words = chunks[0].text.split()
    expected_tail = " ".join(first_words[-30:])
    assert chunks[1].text.startswith(expected_tail)


def test_chunks_never_cross_page_boundary(word_counter):
    pages = [make_page(1, paragraph("a", 300)), make_page(2, paragraph("b", 300))]
    chunks = chunk_pages(
        pages,
        chunk_size=250,
        chunk_overlap=30,
        count_tokens=word_counter,
    )
    pages_in_chunks = [chunk.page_number for chunk in chunks]
    assert pages_in_chunks == sorted(pages_in_chunks)
    assert set(pages_in_chunks) == {1, 2}
    # в чанке первой страницы нет слов второй и наоборот
    for chunk in chunks:
        markers = {w[0] for w in chunk.text.split()}
        assert markers == {("a" if chunk.page_number == 1 else "b")}


def test_oversized_paragraph_split_by_words(word_counter):
    text = paragraph("big", 600)  # один абзац больше chunk_size
    chunks = chunk_pages(
        [make_page(1, text)],
        chunk_size=100,
        chunk_overlap=10,
        count_tokens=word_counter,
    )
    assert len(chunks) >= 6
    assert all(word_counter(chunk.text) <= 100 for chunk in chunks)
    # текст не потерялся и не задублировался (по множеству слов)
    all_words = [w for chunk in chunks for w in chunk.text.split()]
    assert len(set(all_words)) == 600


def test_overlap_must_be_less_than_chunk_size(word_counter):
    with pytest.raises(ValueError):
        chunk_pages(
            [make_page(1, "текст")],
            chunk_size=100,
            chunk_overlap=100,
            count_tokens=word_counter,
        )


def test_tail_within_budget_respects_budget(word_counter):
    text = " ".join(f"w{i}" for i in range(100))
    tail = _tail_within_budget(text, budget=7, count=word_counter)
    assert tail == " ".join(f"w{i}" for i in range(93, 100))
