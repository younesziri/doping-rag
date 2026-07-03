"""Qdrant client + collection setup (the vector-store infrastructure)."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.config import settings
from src.retrieval.embed import EMBED_DIM


def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(client: QdrantClient, *, recreate: bool = False) -> None:
    """Making sure the collection exists with the right vector schema.


    recreate=True drops and rebuilds the collection first, to be used for re-ingestion if I change the chunking
    for example
    """
    name = settings.qdrant_collection

    if recreate and client.collection_exists(name):
        client.delete_collection(name)

    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
