"""Text embedder for the ingestion pipeline.

Embeds chunk texts via the Ollama embeddings API using the model specified
by the ``EMBEDDING_MODEL`` environment variable.

Usage::

    from memory.embedder import embed

    vectors = embed(["Some text to embed."])
    # -> [[0.012, -0.034, ...]]
"""

from __future__ import annotations

import os

import httpx

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_OLLAMA_URL: str = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed(texts: list[str]) -> list[list[float]]:
    """Embed one or more texts using the model from ``EMBEDDING_MODEL``.

    Each text is sent as a separate request to the Ollama embeddings API at
    ``POST {OLLAMA_URL}/api/embeddings`` with payload
    ``{"model": ..., "prompt": text}``.

    Args:
        texts: A list of text strings to embed.  Each must be non-empty.

    Returns:
        A list of vectors (``list[list[float]]``), one per input text.
        Dimensionality matches the embedding model (e.g. 768 for
        ``nomic-embed-text``).

    Raises:
        ValueError: If ``EMBEDDING_MODEL`` is not set, or if *texts*
            contains an empty string.
        httpx.HTTPStatusError: If the Ollama API returns a non-2xx status.
        httpx.RequestError: If the Ollama endpoint is unreachable.

    Example:
        >>> vectors = embed(["Qdrant is a vector database."])
        >>> len(vectors)
        1
        >>> len(vectors[0])
        768
    """
    ollama_url = os.getenv("OLLAMA_URL", _DEFAULT_OLLAMA_URL)
    model = os.environ.get("EMBEDDING_MODEL")
    if not model:
        raise ValueError(
            "EMBEDDING_MODEL environment variable is not set. "
            "Set it to the Ollama model name (e.g. 'nomic-embed-text')."
        )

    # Validate inputs
    for i, t in enumerate(texts):
        if not t or not t.strip():
            raise ValueError(
                f"texts[{i}] is empty — each text must be non-empty for embedding."
            )

    endpoint = f"{ollama_url.rstrip('/')}/api/embeddings"
    result: list[list[float]] = []

    with httpx.Client() as client:
        for text in texts:
            response = client.post(
                endpoint,
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            embedding: list[float] = data["embedding"]
            result.append(embedding)

    return result
