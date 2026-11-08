"""Тесты форматирования источников цитирования (RetrievalService.format_sources)."""

from src.retrieval.search import RetrievalService, RetrievedChunk


def chunk(file_name: str, page: int) -> RetrievedChunk:
    return RetrievedChunk(
        text="...", page_number=page, file_name=file_name, document_id="d", score=0.9
    )


def test_single_source():
    line = RetrievalService.format_sources([chunk("договор.pdf", 12)])
    assert line == "Источник: договор.pdf, стр. 12"


def test_duplicates_are_merged_in_relevance_order():
    chunks = [chunk("a.pdf", 1), chunk("a.pdf", 1), chunk("b.pdf", 3), chunk("a.pdf", 2)]
    line = RetrievalService.format_sources(chunks)
    assert line == "Источники: a.pdf, стр. 1; b.pdf, стр. 3; a.pdf, стр. 2"


def test_empty_chunks_give_empty_line():
    assert RetrievalService.format_sources([]) == ""
