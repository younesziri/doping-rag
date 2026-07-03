"""Search: embedding a query and retrieving the top-k nearest chunks (the READ side)."""

from dataclasses import dataclass

from src.config import settings

from src.retrieval.embed import embed_texts
from src.retrieval.client import get_client
from qdrant_client.models import Filter, FieldCondition, MatchValue


@dataclass
class RetrievedChunk:
    """One search hit: the chunk's payload fields plus its similarity score."""

    chunk_id: str
    text: str
    source: str
    version: str
    pages: list[int]
    score: float


def retrieve(
    query: str,
    top_k: int = settings.top_k,
    version: str | None = None,
) -> list[RetrievedChunk]:
    """Returns the top_k chunks most similar to `query`, optionally filtered by version."""
    vectors, _ = embed_texts([query])
    query_vector = vectors[0]
    client = get_client()
    query_filter: Filter | None = None
    if version is not None:
        query_filter = Filter(must=[FieldCondition(key="version", match=MatchValue(value=version))])
    result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        query_filter=query_filter,
    )

    return [
        RetrievedChunk(
            chunk_id=r.payload["chunk_id"],
            text=r.payload["text"],
            source=r.payload["source"],
            version=r.payload["version"],
            pages=r.payload["pages"],
            score=r.score,
        )
        for r in result.points
    ]


if __name__ == "__main__":
    import sys

    default_q = "What is the sanction for a first anti-doping rule violation?"
    query = sys.argv[1] if len(sys.argv) > 1 else default_q
    hits = retrieve(query)
    print(f"query: {query!r}\n")
    for h in hits:
        print(f"[{h.score:.3f}] {h.source} v{h.version} pages={h.pages}")
        print(f"    {h.text[:160].strip()}...\n")
