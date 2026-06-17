"""Load WADA PDFs and strip page furniture (running headers/footers, page numbers).

Baseline loader: flat text extraction plus light, content-based cleanup. It
deliberately does NOT fix multi-column heading displacement — that's a measured
experiment for later, once the eval harness can score whether the fix helps.
"""

from collections import Counter
from pathlib import Path

import pymupdf


def load_pages(pdf_path: Path) -> list[str]:
    """Return the raw extracted text of each page, in document order."""
    doc = pymupdf.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


def find_boilerplate(pages: list[str], min_fraction: float = 0.5) -> set[str]:
    """Lines that repeat on at least `min_fraction` of pages are page furniture.

    A running header like "World Anti-Doping Code 2021" appears on nearly every
    page, so counting how many pages each line shows up on makes it rise to the
    top. Detecting boilerplate by *repetition* means we never hardcode a
    document-specific string — the same code works for any WADA PDF.
    """
    pages_containing = Counter()
    for text in pages:
        # count each distinct line once per page, not once per occurrence
        for line in {ln.strip() for ln in text.splitlines() if ln.strip()}:
            pages_containing[line] += 1

    threshold = max(2, int(min_fraction * len(pages)))
    return {line for line, n in pages_containing.items() if n >= threshold}


def clean_page(text: str, boilerplate: set[str]) -> str:
    """Drop boilerplate lines and bare page-number lines."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in boilerplate:
            continue
        if stripped.isdigit():  # a line that is only a page number
            continue
        kept.append(stripped)
    return "\n".join(kept)


def load_and_clean(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, cleaned_text)] for a document; pages are 1-indexed."""
    pages = load_pages(pdf_path)
    boilerplate = find_boilerplate(pages)
    out = []
    for page_num, text in enumerate(pages, start=1):
        cleaned = clean_page(text, boilerplate)
        if cleaned.strip():  # skip pages that are empty after cleaning
            out.append((page_num, cleaned))
    return out


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/wada-code-2021-en.pdf")
    raw = load_pages(target)
    boiler = find_boilerplate(raw)
    print(f"{target.name}: {len(raw)} pages")
    print(f"detected {len(boiler)} boilerplate line(s):")
    for line in sorted(boiler):
        print(f"   · {line!r}")
    print(f"\n{len(load_and_clean(target))} non-empty pages after cleaning")
