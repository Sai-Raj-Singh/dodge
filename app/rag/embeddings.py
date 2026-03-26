"""Embedding utilities.

For document indexing: uses ChromaDB's built-in default embedding model
(all-MiniLM-L6-v2 via onnxruntime — runs locally, no API limits).

For query-time Gemini embedding: kept as optional fallback.
"""

import sys

import google.generativeai as genai

from app.config import settings


_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


def embed_query_gemini(query: str) -> list[float]:
    """Generate a Gemini embedding for a single search query (1 API call)."""
    _ensure_configured()
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=query,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]
