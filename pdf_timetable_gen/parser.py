"""PDF Parser — extract raw text from PDF files page by page."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PageText(NamedTuple):
    """One page of extracted text."""

    page_number: int
    text: str


class ParsedPDF(NamedTuple):
    """Full PDF parsed result."""

    file_path: Path
    total_pages: int
    pages: list[PageText]

    def full_text(self) -> str:
        """Concatenate all pages with page markers."""
        return "\n".join(f"--- Page {p.page_number} ---\n{p.text}" for p in self.pages)

    def get_page(self, n: int) -> str:
        """Get text for a specific 1-indexed page."""
        for p in self.pages:
            if p.page_number == n:
                return p.text
        raise ValueError(f"Page {n} not found (PDF has {self.total_pages} pages)")


def parse_pdf(path: str | Path) -> ParsedPDF:
    """Parse a PDF file and extract text from every page.

    Args:
        path: Path to the PDF file.

    Returns:
        ParsedPDF with per-page text.

    Raises:
        FileNotFoundError: If the PDF doesn't exist.
        ValueError: If the file isn't a valid PDF.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {path}")

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(PageText(page_number=i, text=text))
        logger.debug("Page %d: %d chars", i, len(text))

    logger.info("Parsed %s: %d pages, ~%d chars", path.name, len(pages), sum(len(p.text) for p in pages))
    return ParsedPDF(file_path=path, total_pages=len(pages), pages=pages)
