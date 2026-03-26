from __future__ import annotations

from pathlib import Path

import fitz
from loguru import logger


class PageContent:
    __slots__ = ("page_number", "text")

    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text


def extract_pdf_pages(file_path: Path | str) -> list[PageContent]:
    """Extract text from each page of a PDF file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    pages: list[PageContent] = []
    try:
        doc = fitz.open(str(file_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                pages.append(PageContent(page_number=page_num + 1, text=text))
        doc.close()
    except Exception as e:
        logger.error(f"Failed to process PDF {file_path.name}: {e}")
        raise

    logger.info(f"Extracted {len(pages)} pages from {file_path.name}")
    return pages


def get_pdf_page_count(file_path: Path | str) -> int:
    """Return the total number of pages in a PDF."""
    doc = fitz.open(str(file_path))
    count = len(doc)
    doc.close()
    return count
