"""Fixed-size token chunking for cleaned WADA pages.

Turns the `(page_number, cleaned_text)` pairs from `load.load_and_clean` into
`Chunk` objects of ~`chunk_size` tokens with `chunk_overlap` tokens of overlap.

Why tokens (not characters): the embedding model has a token budget and counts
in tokens, so we size chunks in the model's own unit. We use the model's exact
encoding (derived from `settings.embedding_model`) so our "512" equals its 512.

Why overlap: a fixed window can slice an idea in half; re-including the last
`chunk_overlap` tokens in the next chunk means a cut idea still appears whole in
a neighbour. The cost is duplicated tokens -> more chunks -> more embedding spend.

Page provenance: we tokenize page by page and keep each token's page of origin,
so a chunk can record the exact page span it came from (needed later for
citations). Pages are joined with a separator so words don't glue across the
page boundary.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import tiktoken

from src.config import settings
from src.ingestion.load import load_and_clean

SOURCES_PATH = Path("data/raw/sources.json")

# Separator inserted between pages before tokenizing, so the last word of one
# page does not glue onto the first word of the next.
PAGE_SEPARATOR = "\n"


@dataclass
class Chunk:
    """One retrievable unit: text plus the metadata needed to cite and filter it."""

    chunk_id: str
    text: str
    source: str  # filename, e.g. "wada-code-2021-en.pdf"
    version: str  # e.g. "2021" (from the sources.json manifest)
    pages: list[int]  # the distinct page numbers this chunk's tokens came from
    token_count: int


def get_encoding() -> tiktoken.Encoding:
    """The tokenizer the embedding model itself uses (single source of truth)."""
    return tiktoken.encoding_for_model(settings.embedding_model)


def lookup_version(filename: str, manifest_path: Path = SOURCES_PATH) -> str:
    """Reading the authoritative `version` for a file from the provenance manifest.

    Using sources.json (rather than parsing the filename) keeps a single source
    of truth for per-document metadata.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for doc in manifest["documents"]:
        if doc["filename"] == filename:
            return doc["version"]
    raise KeyError(f"{filename!r} not found in {manifest_path}")


def chunk_document(
    pages: list[tuple[int, str]],
    source: str,
    version: str,
    encoding: tiktoken.Encoding,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[Chunk]:
    """Spliting one document's cleaned pages into overlapping fixed-size token chunks."""

    tokens = []
    for page_nb, txt in pages:
        txt += PAGE_SEPARATOR
        token_ids = encoding.encode(txt)
        for token_id in token_ids:
            tokens.append((token_id, page_nb))

    stride = chunk_size - chunk_overlap
    chunks: list[Chunk] = []
    for i, start in enumerate(range(0, len(tokens), stride)):
        window = tokens[start : start + chunk_size]
        #  the last window may be shorter than chunk_size (we keep it)

        chunk_pages = []
        chunk_text = ""
        token_ids = [tid for tid, pg in window]
        chunk_text = encoding.decode(token_ids)
        chunk_pages = sorted({pg for tid, pg in window})
        chunk = Chunk(
            chunk_id=f"{source}::{i}",
            text=chunk_text,
            source=source,
            version=version,
            pages=chunk_pages,
            token_count=len(window),
        )
        chunks.append(chunk)
        if start + chunk_size >= len(tokens):
            break  # I don't want to emit a redundant smaller window that's fully contained in the previous one.

    return chunks

    raise NotImplementedError("chunk_document: write the flatten + sliding-window core")
    # --------------------------------------------------------------------------


def chunk_pdf(pdf_path: Path) -> list[Chunk]:
    """Convenience wiring: load + clean + look up version + chunk one PDF."""
    pages = load_and_clean(pdf_path)
    version = lookup_version(pdf_path.name)
    return chunk_document(pages, source=pdf_path.name, version=version, encoding=get_encoding())


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/wada-code-2021-en.pdf")
    chunks = chunk_pdf(target)

    print(
        f"{target.name}: {len(chunks)} chunks "
        f"(size={settings.chunk_size}, overlap={settings.chunk_overlap})"
    )
    if chunks:
        counts = [c.token_count for c in chunks]
        print(
            f"token_count  min={min(counts)}  max={max(counts)}  "
            f"avg={sum(counts) / len(counts):.0f}"
        )
        sample = chunks[0]
        print(
            f"\nsample chunk  id={sample.chunk_id}  pages={sample.pages}  "
            f"tokens={sample.token_count}"
        )
        print("-" * 70)
        print(sample.text[:500])
