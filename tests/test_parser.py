from dataclasses import fields

from pdf_timetable_gen.parser import PageText, ParsedPDF


def test_page_text_dataclass():
    p = PageText(page_number=1, text="Introduction to Algorithms")
    assert p.page_number == 1
    assert "Algorithms" in p.text


def test_parsed_pdf_dataclass():
    p = ParsedPDF(
        title="Mathematics",
        total_pages=10,
        pages=[PageText(page_number=1, text="Chapter 1: Algebra")],
    )
    assert p.title == "Mathematics"
    assert p.total_pages == 10
    assert len(p.pages) == 1
    assert p.pages[0].page_number == 1


def test_parsed_pdf_fields():
    expected = {f.name for f in fields(ParsedPDF)}
    expected_fields = {"title", "total_pages", "pages"}
    assert expected == expected_fields


def test_page_text_fields():
    expected = {f.name for f in fields(PageText)}
    expected_fields = {"page_number", "text"}
    assert expected == expected_fields
