"""Tests for the PDF parser module."""

from pathlib import Path

from pdf_timetable_gen.parser import PageText, ParsedPDF


def test_page_text_fields():
    """PageText stores page number and text."""
    p = PageText(page_number=3, text="Chapter 1: Algebra")
    assert p.page_number == 3
    assert "Algebra" in p.text


def test_parsed_pdf_fields():
    """ParsedPDF stores file_path, total_pages, and pages list."""
    pages = [PageText(page_number=1, text="Intro"), PageText(page_number=2, text="Body")]
    pdf = ParsedPDF(
        file_path=Path("test.pdf"),
        total_pages=2,
        pages=pages,
    )
    assert pdf.total_pages == 2
    assert len(pdf.pages) == 2
    assert pdf.pages[1].text == "Body"


def test_parsed_pdf_full_text():
    """full_text() concatenates pages with page markers."""
    pages = [PageText(page_number=1, text="Hello"), PageText(page_number=2, text="World")]
    pdf = ParsedPDF(file_path=Path("test.pdf"), total_pages=2, pages=pages)
    result = pdf.full_text()
    assert "--- Page 1 ---" in result
    assert "Hello" in result
    assert "--- Page 2 ---" in result
    assert "World" in result


def test_parsed_pdf_get_page():
    """get_page() returns text for a specific page."""
    pages = [PageText(page_number=1, text="First"), PageText(page_number=5, text="Fifth")]
    pdf = ParsedPDF(file_path=Path("test.pdf"), total_pages=5, pages=pages)
    assert pdf.get_page(1) == "First"
    assert pdf.get_page(5) == "Fifth"


def test_parsed_pdf_get_page_raises():
    """get_page() raises ValueError for missing page."""
    pages = [PageText(page_number=1, text="First")]
    pdf = ParsedPDF(file_path=Path("test.pdf"), total_pages=1, pages=pages)
    try:
        pdf.get_page(99)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
