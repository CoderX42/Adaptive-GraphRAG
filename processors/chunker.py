from __future__ import annotations

from core.models import Chunk
from processors.pdf_processor import PageContent


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1.5 chars per CJK token, ~4 chars per English token."""
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_count = len(text) - cjk_count
    return int(cjk_count / 1.5 + ascii_count / 4)


def chunk_pages(
    pages: list[PageContent],
    doc_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 128,
) -> list[Chunk]:
    """Split page texts into overlapping chunks using a sliding-window strategy."""
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text
        if not text:
            continue

        start = 0
        while start < len(text):
            end = _find_chunk_boundary(text, start, chunk_size)
            segment = text[start:end].strip()

            if segment:
                chunks.append(
                    Chunk(
                        doc_id=doc_id,
                        content=segment,
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        metadata={"char_start": start, "char_end": end},
                    )
                )
                chunk_index += 1

            if end >= len(text):
                break
            start = max(start + 1, end - _chars_for_tokens(chunk_overlap))

    return chunks


def _chars_for_tokens(tokens: int) -> int:
    """Convert a rough token count into a character count for slicing."""
    return tokens * 3


def _find_chunk_boundary(text: str, start: int, chunk_size_tokens: int) -> int:
    """Find a good chunk boundary near the target token count, preferring sentence endings."""
    target_chars = start + _chars_for_tokens(chunk_size_tokens)
    end = min(target_chars, len(text))

    if end >= len(text):
        return len(text)

    separators = ["。", "！", "？", ".\n", "\n\n", ". ", "\n"]
    search_region_start = max(start, end - 200)
    for sep in separators:
        pos = text.rfind(sep, search_region_start, end)
        if pos > start:
            return pos + len(sep)

    return end
