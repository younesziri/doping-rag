"""Annotation helper: turn questions into candidate gold locations to hand-label.

Usage:
    uv run python -m src.evaluation.annotate "your question" [--version 2021] [--k 8]
    uv run python -m src.evaluation.annotate data/eval/_candidates_batch1.txt [--k 8]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from src.retrieval.search import retrieve

_NUM = re.compile(r"^\s*\d+[.)]\s*")  # a leading "12. " list number
_TAG = re.compile(r"\s*\[(\w+)\]\s*$")  # a trailing "[register]" tag


def _skeleton(question: str, hits, register: str | None, version: str | None) -> dict:
    """Paste-ready row pre-filled from the TOP hit (edit `gold` to the real answer)."""
    tags = [register] if register else []
    if not hits:  # no hits -> pre-label as unanswerable, but VERIFY (widen --k first)
        return {
            "id": "qNNN",
            "question": question,
            "answerable": False,
            "reference_answer": None,
            "gold": [],
            "version_target": version,
            "tags": tags,
            "source": "llm-cleanroom",
            "notes": "no hits — verify OOC",
        }
    top = hits[0]
    return {
        "id": "qNNN",
        "question": question,
        "answerable": True,
        "reference_answer": "TODO: write the gold answer in your own words",
        "gold": [{"source": top.source, "pages": top.pages, "chunk_ids": [top.chunk_id]}],
        "version_target": version,
        "tags": tags,
        "source": "llm-cleanroom",
        "notes": None,
    }


def annotate(question: str, k: int = 8, version: str | None = None) -> None:
    """Single-question mode: print candidates + skeleton to stdout."""
    hits = retrieve(question, top_k=k, version=version)
    print(f"\nquestion: {question!r}")
    if version:
        print(f"version filter: {version}")
    print("=" * 88)
    for rank, h in enumerate(hits, start=1):
        print(
            f"[{rank}] score={h.score:.3f}  {h.source}  v{h.version}  pages={h.pages}  id={h.chunk_id}"
        )
        print(f"     {' '.join(h.text.split())[:220]}...")
        print("-" * 88)
    if not hits:
        print("(no hits — is the collection indexed / the version filter too narrow?)")
        return
    print("paste-ready skeleton (edit `gold` to the chunk that truly answers it):")
    print(json.dumps(_skeleton(question, hits, None, version), indent=2, ensure_ascii=False))


def _parse_line(line: str) -> tuple[str, str | None]:
    """Strip a leading list number and a trailing [register] tag → (question, register)."""
    register = None
    m = _TAG.search(line)
    if m:
        register = m.group(1)
        line = line[: m.start()]
    return _NUM.sub("", line).strip(), register


def annotate_file(path: Path, k: int = 8, out: Path | None = None) -> Path:
    """Batch mode: read questions from `path`, write a markdown review to `out`."""
    out = out or path.with_suffix(".review.md")
    lines = [
        ln
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    parts = [
        f"# Candidate review — {path.name} ({len(lines)} questions)\n",
        "Score ~0.6+ usually = a real hit; a collapsed top score (~0.3 or below) is a "
        "signal the question may be out-of-corpus. You decide gold; edit the skeleton.\n",
    ]
    for i, ln in enumerate(lines, start=1):
        question, register = _parse_line(ln)
        hits = retrieve(question, top_k=k)
        parts.append(f"\n## {i:02d}. [{register or '?'}]  {question}\n")
        if hits:
            parts.append("| rank | score | source | pages | chunk_id |")
            parts.append("|---|---|---|---|---|")
            for rank, h in enumerate(hits, start=1):
                parts.append(
                    f"| {rank} | {h.score:.3f} | {h.source} | {h.pages} | `{h.chunk_id}` |"
                )
            parts.append("")
            for rank, h in enumerate(hits, start=1):
                parts.append(
                    f"**[{rank}] {h.score:.3f} — {h.source} v{h.version} "
                    f"pages={h.pages} — `{h.chunk_id}`**\n"
                )
                parts.append("```text")
                parts.append(h.text.strip())
                parts.append("```")
        else:
            parts.append("_(no hits)_")
        parts.append("\n```json")
        parts.append(json.dumps(_skeleton(question, hits, register, None), ensure_ascii=False))
        parts.append("```")
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def _parse_argv(argv: list[str]) -> tuple[str, int, str | None]:
    args = list(argv)
    version: str | None = None
    k = 8
    if "--version" in args:
        i = args.index("--version")
        version = args[i + 1]
        del args[i : i + 2]
    if "--k" in args:
        i = args.index("--k")
        k = int(args[i + 1])
        del args[i : i + 2]
    return " ".join(args), k, version


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m src.evaluation.annotate "question" [--version 2021] [--k 8]')
        print("   or: python -m src.evaluation.annotate <questions_file> [--k 8]")
        raise SystemExit(1)
    arg, k, version = _parse_argv(sys.argv[1:])
    target = Path(arg)
    if target.is_file():
        written = annotate_file(target, k=k)
        print(f"wrote review → {written}  ({k} candidates/question)")
    else:
        annotate(arg, k=k, version=version)
