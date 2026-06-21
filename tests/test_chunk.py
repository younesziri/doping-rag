"""Tests for fixed-size token chunking (src/ingestion/chunk.py).

These test `chunk_document` directly on synthetic pages — no PDF, no network —
so they are fast and deterministic.
"""

import math

import pytest

from src.ingestion.chunk import PAGE_SEPARATOR, chunk_document, get_encoding

SOURCE = "test-doc.pdf"
VERSION = "2026"


@pytest.fixture
def encoding():
    """The real tiktoken encoding, shared across tests in this module."""
    return get_encoding()


def _pages_from(*texts: str) -> list[tuple[int, str]]:
    """Builds `[(1, texts[0]), (2, texts[1]), ...]` — synthetic cleaned pages."""
    return [(page_nb, text) for page_nb, text in enumerate(texts, start=1)]


def _expected_chunk_count(n_tokens: int, size: int, overlap: int) -> int:
    stride = size - overlap
    if n_tokens == 0:
        return 0
    if n_tokens <= size:
        return 1
    return math.ceil((n_tokens - size) / stride) + 1


def test_chunk_sizes(encoding):
    """Every chunk is <= chunk_size tokens, and all but the last are exactly it."""
    pages = _pages_from("regulation " * 200)  # one long page -> several chunks
    chunks = chunk_document(pages, SOURCE, VERSION, encoding, chunk_size=50, chunk_overlap=10)

    #
    # every chunk except the last has token_count == 50 (the tail may be shorter).
    for chunk in chunks[:-1]:
        assert chunk.token_count == 50
    assert chunks[-1].token_count <= 50


def test_chunk_count_matches_stride(encoding):
    """The number of chunks follows the stride formula (overlap accounted for)."""
    text = "regulation " * 200
    pages = _pages_from(text)
    chunks = chunk_document(pages, SOURCE, VERSION, encoding, chunk_size=50, chunk_overlap=10)

    sum_test_tokens = sum(len(encoding.encode(t + PAGE_SEPARATOR)) for _, t in pages)
    assert len(chunks) == _expected_chunk_count(sum_test_tokens, 50, 10)


def test_page_provenance(encoding):
    """A chunk spanning a page boundary records both page numbers, sorted."""
    # Two short pages whose combined tokens fit in one big window -> one chunk
    pages = _pages_from("alpha beta gamma", "delta epsilon zeta")
    chunks = chunk_document(pages, SOURCE, VERSION, encoding, chunk_size=512, chunk_overlap=64)

    assert len(chunks) == 1 and chunks[0].pages == [1, 2]
    # there is exactly one chunk and its .pages == [1, 2]


def test_chunk_ids_are_sequential_and_unique(encoding):
    """chunk_id is f"{source}::{i}" for i = 0..n-1, and all ids are unique."""
    pages = _pages_from("regulation " * 200)
    chunks = chunk_document(pages, SOURCE, VERSION, encoding, chunk_size=50, chunk_overlap=10)

    assert [c.chunk_id for c in chunks] == [f"{SOURCE}::{i}" for i in range(len(chunks))]
