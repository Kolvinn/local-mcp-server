"""Embedder module for producing dense, sparse, and late-interaction vectors.

Provides the ``Embedder`` class and a module-level singleton accessor.
Refactored from ``src/hybrid_embed_test.py`` lines 61-116.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastembed import LateInteractionTextEmbedding, SparseTextEmbedding
from litellm import embedding as litellm_embedding
from qdrant_client.models import SparseVector

# ---------------------------------------------------------------------------
# Configuration (from environment)
# ---------------------------------------------------------------------------

LITE_LLM_URL: str = os.getenv("LITE_LLM_URL", "http://litellm:4000")
LITE_LLM_API_KEY: str = os.getenv("LITE_LLM_API_KEY", "sk-1234")
DENSE_MODEL: str = os.getenv("DENSE_MODEL", "openai/nomic-embed")
SPARSE_MODEL: str = os.getenv("SPARSE_MODEL", "prithivida/Splade_PP_en_v1")
LI_MODEL: str = os.getenv(
    "LI_MODEL", "answerdotai/answerai-colbert-small-v1"
)
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek/deepseek-flash")
DIM_SIZE: int = int(os.getenv("DIM_SIZE", "768"))
LI_DIM_SIZE: int = int(os.getenv("LI_DIM_SIZE", "128"))

# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class EmbeddingError(RuntimeError):
    """Raised when LiteLLM or FastEmbed embedding generation fails."""


# ---------------------------------------------------------------------------
# EmbedType enum
# ---------------------------------------------------------------------------


class EmbedType(str, Enum):
    """Type of embedding vector to produce."""

    DENSE = "dense"
    SPARSE = "sparse"
    LATE_INTERACTION = "multi"


# ---------------------------------------------------------------------------
# Module-level lazy-init singletons (shared across all Embedder instances)
# ---------------------------------------------------------------------------

_sparse_model: SparseTextEmbedding | None = None
_li_model: LateInteractionTextEmbedding | None = None


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------


class Embedder:
    """Produce dense, sparse, and late-interaction vectors for a given text.

    Configuration is read from environment variables at import time (see
    module-level constants above).
    """

    def embed(
        self, text: str, type: EmbedType  # noqa: A002
    ) -> list[float] | SparseVector | list[list[float]]:
        """Embed *text* with the requested *type* of embedding model.

        Args:
            text: The input string to embed.
            type: Which embedding strategy to use.

        Returns:
            - For ``DENSE``: a ``list[float]`` of length ``DIM_SIZE`` (768).
            - For ``SPARSE``: a ``SparseVector`` with ``indices`` and
              ``values``.
            - For ``LATE_INTERACTION``: a ``list[list[float]]`` of shape
              ``(tokens, LI_DIM_SIZE)``.

        Raises:
            ConnectionError: If LiteLLM is unreachable (dense path).
            EmbeddingError: If FastEmbed fails to load (sparse / LI paths)
                or if the embedding response contains no data.
        """
        global _sparse_model, _li_model  # noqa: PLW0603

        if type == EmbedType.DENSE:
            return self._embed_dense(text)

        if type == EmbedType.SPARSE:
            if _sparse_model is None:
                try:
                    _sparse_model = SparseTextEmbedding(
                        model_name=SPARSE_MODEL,
                        cuda=False,
                    )
                except Exception as exc:
                    raise EmbeddingError(
                        f"Failed to load sparse model {SPARSE_MODEL}: {exc}"
                    ) from exc
            return self._embed_sparse(text)

        # LATE_INTERACTION
        if _li_model is None:
            try:
                _li_model = LateInteractionTextEmbedding(LI_MODEL)
            except Exception as exc:
                raise EmbeddingError(
                    f"Failed to load late-interaction model {LI_MODEL}: {exc}"
                ) from exc
        return self._embed_li(text)

    # ------------------------------------------------------------------
    # Private per-type helpers
    # ------------------------------------------------------------------

    def _embed_dense(self, text: str) -> list[float]:
        """Produce a dense vector via LiteLLM."""
        try:
            resp = litellm_embedding(
                api_base=LITE_LLM_URL,
                api_key=LITE_LLM_API_KEY,
                model=DENSE_MODEL,
                input=text,
            )
        except Exception as exc:
            raise ConnectionError(
                f"LiteLLM unreachable at {LITE_LLM_URL}: {exc}"
            ) from exc

        try:
            return resp.data[0]["embedding"]  # type: ignore[index]
        except (IndexError, KeyError, TypeError) as exc:
            raise EmbeddingError(
                "Embedding response has no data[0] or missing 'embedding' key"
            ) from exc

    def _embed_sparse(self, text: str) -> SparseVector:
        """Produce a sparse vector via FastEmbed SparseTextEmbedding."""
        assert _sparse_model is not None  # already lazy-initialised
        try:
            results = list(_sparse_model.embed([text]))
            sparse = results[0]
        except Exception as exc:
            raise EmbeddingError(
                f"Sparse embedding failed: {exc}"
            ) from exc

        return SparseVector(
            indices=sparse.indices.tolist(),
            values=sparse.values.tolist(),
        )

    def _embed_li(self, text: str) -> list[list[float]]:
        """Produce a late-interaction (ColBERT-style) multi-vector."""
        assert _li_model is not None  # already lazy-initialised
        try:
            results = list(_li_model.embed([text]))
            return results[0].tolist()
        except Exception as exc:
            raise EmbeddingError(
                f"Late-interaction embedding failed: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_embedder_instance: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the module-level singleton ``Embedder`` instance.

    The embedder is lazily created on the first call and reused thereafter.
    """
    global _embedder_instance  # noqa: PLW0603
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance
