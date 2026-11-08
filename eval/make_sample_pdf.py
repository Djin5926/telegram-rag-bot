"""Генерирует eval/samples/sample.pdf — вымышленный договор с конкретными фактами.

Файл детерминированный: вопросы в eval/questions.jsonl привязаны к этим фактам.
Запуск: python eval/make_sample_pdf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf as fitz

SAMPLES_DIR = Path(__file__).parent / "samples"
OUTPUT = SAMPLES_DIR / "sample.pdf"

# Кандидаты системных шрифтов с поддержкой кириллицы (Windows / macOS / Linux)
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4, пункты
MARGIN = 60
TITLE = 'ДОГОВОР ОКАЗАНИЯ ОБЛАЧНЫХ УСЛУГ № 2026-117 от 15 марта 2026 года'

SECTIONS: list[tuple[str, str]] = [
    (
        "1. Предмет договора",
        "Исполнитель обязуется предоставить Заказчику вычислительные мощности облачного "
        "серверного кластера «Сигма» (далее — Услуги), а Заказчик обязуется принимать и "
        "оплачивать Услуги в соответствии с условиями настоящего Договора.",
    ),
    (
        "2. Срок действия",
        "Договор вступает в силу 1 апреля 2026 года и действует по 31 марта 2027 года "
        "(12 месяцев). Договор автоматически продлевается на каждый следующий год, если "
        "ни одна из сторон не заявит в письменной форме об отказе от продления "
        "не позднее чем за 30 календарных дней до окончания срока действия.",
    ),
    (
        "3. Стоимость и порядок оплаты",
        "Стоимость Услуг составляет 145 000 (сто сорок пять тысяч) рублей в месяц, "
        "НДС 20% включён в указанную стоимость. Оплата производится авансом "
        "до 5-го числа текущего месяца на основании счёта Исполнителя.",
    ),
    (
        "4. Уровень обслуживания (SLA)",
        "Гарантируемый уровень доступности Услуг составляет 99,9% в течение календарного "
        "месяца. За каждый полный час простоя сверх одного часа в месяц Исполнитель "
        "выплачивает Заказчику неустойку в размере 5% месячной платы. Совокупный размер "
        "неустойки не может превышать 50% месячной платы.",
    ),
    (
        "5. Техническая поддержка",
        "Поддержка оказывается круглосуточно (24/7). Время реакции на инциденты "
        "критического уровня — не более 30 минут с момента регистрации обращения.",
    ),
    (
        "6. Персональные данные и размещение данных",
        "Стороны обрабатывают персональные данные в соответствии с Федеральным законом "
        "№ 152-ФЗ «О персональных данных». Все серверы, на которых размещаются данные "
        "Заказчика, находятся на территории Российской Федерации.",
    ),
    (
        "7. Резервное копирование",
        "Резервные копии данных Заказчика создаются автоматически ежедневно в 03:00 по "
        "Москве и хранятся в течение 30 календарных дней.",
    ),
    (
        "8. Расторжение договора",
        "Любая из сторон может расторгнуть Договор в одностороннем порядке, направив "
        "письменное уведомление за 30 календарных дней. При досрочном расторжении "
        "по инициативе Заказчика Заказчик уплачивает штраф в размере 10% стоимости "
        "Услуг за оставшийся период действия Договора.",
    ),
    (
        "9. Претензии и форс-мажор",
        "Претензии рассматриваются в течение 10 рабочих дней с момента получения. "
        "Стороны освобождаются от ответственности при обстоятельствах непреодолимой "
        "силы, подтверждённых уполномоченным органом.",
    ),
]


def _find_cyrillic_font() -> str | None:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def build_pdf(output: Path = OUTPUT) -> Path:
    font_file = _find_cyrillic_font()
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN

    def new_page() -> None:
        nonlocal page, y
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        y = MARGIN

    def ensure_font(current_page: fitz.Page) -> None:
        if font_file:
            current_page.insert_font(fontname="cyr", fontfile=font_file)
        # иначе остаётся встроенный helv (текст будет латиницей)

    def put(text: str, size: float, bold_hint: bool = False) -> None:
        nonlocal page, y
        fontname = "cyr" if font_file else "helv"
        while True:
            ensure_font(page)  # шрифт регистрируется на каждой новой странице
            rect = fitz.Rect(MARGIN, y, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN)
            spare = page.insert_textbox(
                rect, text, fontsize=size, fontname=fontname, lineheight=1.35
            )
            if spare >= 0:
                y = PAGE_HEIGHT - MARGIN - spare + 14
                return
            new_page()

    put(TITLE, size=13)
    put("г. Москва", size=10)
    for heading, body in SECTIONS:
        put(heading, size=11.5)
        put(body, size=10.5)
    put("Подписи сторон: ООО «Облако-42» / ООО «Заказчик»", size=10)

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    doc.close()
    return output


if __name__ == "__main__":
    path = build_pdf()
    print(f"Создан {path} ({path.stat().st_size} байт)")
    if _find_cyrillic_font() is None:
        print(
            "ВНИМАНИЕ: системный шрифт с кириллицей не найден — "
            "текст мог записаться латиницей.",
            file=sys.stderr,
        )
