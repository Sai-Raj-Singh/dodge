"""ChromaDB vector store for RAG retrieval.

Uses ChromaDB's built-in default embedding function (all-MiniLM-L6-v2 via
onnxruntime) for document indexing — runs locally with zero API limits.
Query search also uses the same local model for consistency.
"""

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings


_client = None
COLLECTION_NAME = "sap_o2c_chunks"


def get_client():
    """Get or create a persistent ChromaDB client."""
    global _client
    if _client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    """Get or create the main chunks collection.

    Uses ChromaDB's default embedding function (all-MiniLM-L6-v2)
    which runs locally via onnxruntime — no API key needed.
    """
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(chunks: list[dict]) -> int:
    """Store text chunks in ChromaDB (embeddings generated automatically).

    ChromaDB's default embedding function handles embedding internally
    when you pass `documents` without `embeddings`.

    Args:
        chunks: List of dicts with keys: id, text, metadata.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection()

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Upsert in batches — ChromaDB auto-generates embeddings from documents
    print(
        "[VECTOR] Storing chunks (local embeddings via all-MiniLM-L6-v2)...", flush=True
    )
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.upsert(
            ids=ids[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )
        print(f"  [VECTOR] {end}/{len(ids)} chunks stored", flush=True)

    count = collection.count()
    print(f"[VECTOR] Done: {count} chunks in '{COLLECTION_NAME}'", flush=True)
    return count


def search(query: str, n_results: int = 5, where: Optional[dict] = None) -> list[dict]:
    """Search for similar chunks using a natural language query.

    Uses ChromaDB's built-in embedding function to embed the query
    and find nearest neighbours.

    Args:
        query: The search query string.
        n_results: Number of results to return.
        where: Optional metadata filter (ChromaDB where clause).

    Returns:
        List of dicts with keys: id, text, metadata, distance.
    """
    collection = get_collection()

    kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output = []
    if results and results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i]
                    if results["metadatas"]
                    else {},
                    "distance": results["distances"][0][i]
                    if results["distances"]
                    else 0.0,
                }
            )

    return output


def search_by_type(query: str, entity_type: str, n_results: int = 5) -> list[dict]:
    """Search for chunks of a specific entity type."""
    return search(query, n_results=n_results, where={"type": entity_type})


def get_collection_stats() -> dict:
    """Return basic stats about the vector store."""
    collection = get_collection()
    return {
        "collection": COLLECTION_NAME,
        "count": collection.count(),
    }


def clear_collection() -> None:
    """Delete and recreate the collection."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    print(f"[VECTOR] Collection '{COLLECTION_NAME}' cleared.")
