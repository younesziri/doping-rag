"""Embedding: turn texts into vectors via OpenAI text-embedding-3-small.

Shared by BOTH indexing (embeding the chunks) and search (embeding the query). Keeping
it in one place enforces the single most important invariant of dense retrieval:
documents and queries must be embedded by the same model, or they live in
different coordinate systems and "nearest neighbour" is meaningless.
"""

from openai import OpenAI

from src.config import settings

# Output dimension of text-embedding-3-small. the Qdrant
# collection imports it so the store's geometry always matches the model.
EMBED_DIM = 1536

# How many texts we send per HTTP request.
# Kept well under OpenAI's ~2048-inputs-per-request ceiling and leaves headroom
# for the per-request token cap.
EMBED_BATCH_SIZE = 128

# One client for the whole module.
_client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> tuple[list[list[float]], int]:
    """Embed many texts. Returns (vectors, total_tokens_billed)."""
    vectors: list[list[float]] = []
    total_tokens = 0

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]

        resp = _client.embeddings.create(model=settings.embedding_model, input=batch)

        # Contract invariant: one vector back per input, in input order. Each
        # item also carries `.index`; we sort by it to be defensive rather than
        # trusting the order blindly (a cheap guard against a reordered response).
        for item in sorted(resp.data, key=lambda d: d.index):
            vectors.append(item.embedding)

        total_tokens += resp.usage.total_tokens

    # we MUST get one vector per input,
    assert len(vectors) == len(texts), f"got {len(vectors)} vectors for {len(texts)} texts"

    return vectors, total_tokens
