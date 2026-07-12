"""Eval dataset: schema + loader (the versioned 'ruler' for the whole harness)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

DATASET_DIR = Path("data/eval")
SOURCES_PATH = Path("data/raw/sources.json")


def known_sources() -> set[str]:
    """Filenames the manifest knows about — used to reject a typo'd gold source."""
    manifest = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    return {doc["filename"] for doc in manifest["documents"]}


class GoldLocation(BaseModel):
    """Where the answer lives. `pages` is the durable gold; `chunk_ids` is a snapshot."""

    source: str  # filename, matches Chunk.source / RetrievedChunk.source
    pages: list[int] = Field(min_length=1)  # 1-indexed page span the answer sits in
    chunk_ids: list[str] = []  # convenience snapshot at label time (brittle when I   re-chunk)


class EvalExample(BaseModel):
    """One graded question. `answerable=False` rows are the out-of-corpus probes."""

    id: str  # stable handle, e.g. "q001" — never reuse or renumber
    question: str
    answerable: bool  # True = answer is in the corpus; False = out-of-corpus probe
    reference_answer: str | None = None  # gold answer for the correctness judge (fill later)
    gold: list[GoldLocation] = []  # empty iff not answerable
    version_target: str | None = None  # e.g. "2021"/"2027": which corpus version the Q targets
    tags: list[str] = []  # e.g. "version-sensitive", "cross-reference", "abstention"
    source: str = (
        ""  # provenance: "llm-cleanroom"/"wada-faq"/"self"/"cas" — enables per-source metrics
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> EvalExample:
        # answerable <=> has gold. This is what lets retrieval be scored at all:
        # no gold span => nothing to check recall/MRR against.
        if self.answerable and not self.gold:
            raise ValueError(f"{self.id}: answerable question must have >=1 gold location")
        if not self.answerable and self.gold:
            raise ValueError(f"{self.id}: unanswerable question must have empty gold")
        return self


class EvalDataset(BaseModel):
    version: str  # dataset version, e.g. "v1" ,,stamped into every run report
    examples: list[EvalExample] = []

    @model_validator(mode="after")
    def _check_ids_and_sources(self) -> EvalDataset:
        ids = [e.id for e in self.examples]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate example ids: {dupes}")
        valid = known_sources()
        for e in self.examples:
            for g in e.gold:
                if g.source not in valid:
                    raise ValueError(
                        f"{e.id}: unknown gold source {g.source!r} (not in sources.json)"
                    )
        return self


def load_dataset(version: str = "v1") -> EvalDataset:
    """Load + validate data/eval/<version>.json. Raises loudly on any malformed row."""
    path = DATASET_DIR / f"{version}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return EvalDataset(**data)


if __name__ == "__main__":
    from collections import Counter

    ds = load_dataset()
    ans = sum(e.answerable for e in ds.examples)
    tags = Counter(t for e in ds.examples for t in e.tags)
    print(f"dataset {ds.version}: {len(ds.examples)} examples")
    print(f"  answerable={ans}  unanswerable={len(ds.examples) - ans}")
    if tags:
        print(f"  tags={dict(tags)}")
