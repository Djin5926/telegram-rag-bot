"""Общие фикстуры тестов."""

import pytest


@pytest.fixture
def word_counter():
    """Детерминированный счётчик «токенов» для тестов чанкера: 1 слово = 1 токен."""
    return lambda text: len(text.split())
