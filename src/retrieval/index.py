"""Indexing: embeding chunks and upserting them into Qdrant (the WRITE side)."""

import uuid

from src.config import settings
from src.ingestion.chunk import Chunk, chunk_pdf

from src.retrieval.client import get_client, ensure_collection
from src.retrieval.embed import embed_texts

from qdrant_client.models import PointStruct

# A fixed namespace for uuid5. Deriving it from the built-in DNS namespace + a
# project string keeps it reproducible across runs/machines with no opaque magic
# constant to paste around.
_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "doping-rag")


def point_id(chunk_id: str) -> str:
    """Deterministic Qdrant pt id for a chunk_id."""
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def index_chunks(chunks: list[Chunk], *, recreate: bool = False) -> int:
    """Embedding `chunks` and upserting them as Qdrant points. Returns how many indexed."""
    client = get_client()
    ensure_collection(client, recreate=recreate)

    vectors, total_tokens = embed_texts([c.text for c in chunks])

    assert len(vectors) == len(chunks)

    points: list[PointStruct] = []
    for i, c in enumerate(chunks):
        points.append(
            PointStruct(
                id=point_id(c.chunk_id),
                vector=vectors[i],
                payload={
                    "source": c.source,
                    "version": c.version,
                    "pages": c.pages,
                    "text": c.text,
                    "chunk_id": c.chunk_id,
                },
            )
        )

    client.upsert(collection_name=settings.qdrant_collection, points=points, wait=True)

    print(f"embedded {len(chunks)} chunks · {total_tokens} tokens")
    return len(chunks)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Index one or more PDFs. recreate=True on the FIRST file only: start from a
    # clean collection, but don't wipe earlier files as we add more.
    targets = [Path(a) for a in sys.argv[1:]] or [Path("data/raw/wada-code-2021-en.pdf")]
    total = 0
    for i, target in enumerate(targets):
        chunks = chunk_pdf(target)
        total += index_chunks(chunks, recreate=(i == 0))
        print(f"  {target.name}: {len(chunks)} chunks")
    print(f"indexed {total} chunks into '{settings.qdrant_collection}'")
