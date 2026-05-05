# Qdrant Skill Stack Comparison

**Date:** 2026-05-05

## Three skills — progressive, minimal overlap

| Skill | Role | Size | Best for |
|-------|------|------|----------|
| `qdrant` | REST/curl API reference | 1 file, 273 lines | Quick endpoint lookup, payload filter syntax, distance metric table |
| `qdrant-vector-search` | Python SDK + production RAG | 3 files, ~1,770 lines | **Primary A2 skill**: collections, upsert, search, HNSW, multi-vector, quantization, LangChain/LlamaIndex, sharding, Docker Compose |
| `qdrant-search-quality` | Diagnosis + advanced retrieval | 6 files, ~297 lines | Hybrid search (RRF/DBSF/Formula), HNSW tuning, MMR diversity, relevance feedback, sparse model selection |

## Stack logic

```
qdrant → "How do I talk to Qdrant?" (REST reference)
qdrant-vector-search → "How do I build with Qdrant?" (SDK + patterns)
qdrant-search-quality → "Why are my results bad?" (diagnosis + tuning)
```

## A2 loading recommendation

**Baseline for Qdrant implementer spawns:**
```
python-expert, qdrant-vector-search, async-python-patterns, python-type-safety
```

`qdrant` and `qdrant-search-quality` are reference — load on demand, not baseline.

## What's NOT covered

- Chunking / semantic splitting strategies
- Embedding model specifics (nomic-embed-text via Ollama)
- Config management (pydantic-settings / dotenv)
