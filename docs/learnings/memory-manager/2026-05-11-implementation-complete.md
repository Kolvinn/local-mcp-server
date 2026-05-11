# Memory Manager — Implementation Complete (Learnings & Next Steps)

## What was built
All 5 files implementing the Memory Manager LangGraph spec:

| File | Lines | Role |
|------|-------|------|
| `src/memory/taxonomy_loader.py` | ~90 | Load/schema-validate taxonomy JSON; extract payload index defs |
| `src/memory/embedder.py` | ~170 | Dense (LiteLLM), sparse (FastEmbed SPLADE), late-interaction (FastEmbed ColBERT) |
| `src/memory/qdrant_client.py` | ~180 | Qdrant singleton, named-vector collection creation, idempotent upsert |
| `src/memory/graph.py` | ~310 | 3-node StateGraph + Pydantic models + `ingest()` shortcut |
| `src/memory/__init__.py` | ~80 | 18 exports, preserves existing edge_validator stubs |

---

## Key implementation decisions

### 1. Module-level singleton pattern everywhere
- `Embedder`, `QdrantClient`, taxonomy cache, compiled graph — all module-level lazy-init singletons
- FastEmbed models are module-level (not instance-level) so they're shared across all callers
- This matches the spec's "lazy-init, module-level singletons" direction

### 2. Error-return pattern in graph nodes
- All 3 nodes return `{"error": str}` on failure — never raise inside a node
- The graph always reaches END regardless (no conditional error routing)
- Caller checks `result["error"]` post-invoke

### 3. LLM retry strategy (validate_classify only)
- If LLM JSON parsing fails → retry once with error message injected into prompt
- If retry also fails → return `{"error": "LLM classification failed after retry"}`
- If LLM returns valid JSON but bad taxonomy values → **no retry** (caller/category error)

### 4. Collection creation deferred to first embed_ingest
- Not eager at import time
- `ensure_collection_exists()` is idempotent (checks existence first)
- Payload indexes from taxonomy created after collection, with duplicate-skip

---

## Issues found during implementation

### 🔴 CRITICAL: LI_DIM mismatch
- **Spec says:** `LI_DIM_SIZE = 128` and `DENSE_DIM = 128`
- **Reality:** `answerdotai/answerai-colbert-small-v1` outputs **96-dim** vectors
- **Proof:** Integration test confirmed Qdrant rejected with `expected dim: 128, got 96`
- **Original code** in `hybrid_embed_test.py` correctly used 96
- **Fix:** Change defaults in both `embedder.py` and `qdrant_client.py` to 96, OR switch to a 128-dim model

### 🟡 Graph diagram file reference
- Spec references `docs/diagrams/memory-manager-state.mmd` — this file may not exist yet

---

## Integration test results

The full pipeline was executed (no mocking):
```
ingest(content="Qdrant is a vector database...", source="test", 
       category_type="knowledge", category="definition", tags=["foundational"])
```

| Step | Result |
|------|--------|
| `MemoryManagerInput` validation | ✅ Passed |
| `validate_classify_node` (provided class) | ✅ Skipped LLM, validated against taxonomy |
| `build_payload_node` | ✅ UUID + Payload + PointStruct created |
| `embed_ingest_node` — dense | ✅ 768-dim vector produced |
| `embed_ingest_node` — sparse | ✅ SparseVector produced |
| `embed_ingest_node` — late-interaction | ✅ 96-dim vector produced (wrong — spec expects 128) |
| `ensure_collection_exists()` | ✅ Connected to Qdrant |
| `upsert_point()` | ❌ Rejected — dimension mismatch (128 vs 96) |

Takeaway: **The pipeline works end-to-end except for the LI_DIM configuration bug.**

---

## What needs to be done next (priority ordered)

### P0: Fix LI_DIM mismatch
Either:
- Change `LI_DIM_SIZE` default to `96` and `DENSE_DIM` to `96` in both `embedder.py` and `qdrant_client.py`
- Or switch to a different ColBERT model that produces 128-dim (e.g., `colbert-ir/colbertv2.0`)

### P1: Create accurate test data
Need a `test_data.json` (or similar) with entries covering:

| Scenario | Example |
|----------|---------|
| **4 category_types** | knowledge/definition, objective/goal, learning/technical_lesson, thought/open_question |
| **Full pre-classification** | All fields provided → skips LLM |
| **Partial classification** | Only content + source → triggers LLM |
| **All 4 tag scenarios** | With tags, empty tags, valid tags, invalid tags |
| **Edge cases** | Content near min_length, source variations |
| **Round-trip verification** | ingest → search Qdrant → confirm point exists with correct payload |

### P2: Embedding batching
`Embedder.embed()` processes one text at a time. Switch to batch for:
- Dense: pass multiple texts in single litellm.embedding() call
- Sparse: already batch-capable via `_sparse_model.embed(docs, batch_size=N)`
- LI: already batch-capable via `_li_model.embed(docs, batch_size=N)`

### P3: Qdrant upload method selection
Research whether `client.upload_points()` (batch HTTP upload) is more efficient than repeated `client.upsert()` calls. The spec's general principle is: fewer round-trips = better.

### P4: Auditor tests
The spec test plan (`§8`) lists 17 tests across 3 test files:
- `test_taxonomy_loader.py` — 6 tests
- `test_embedder.py` — 4 tests
- `test_graph.py` — 8 tests

These should be written and verified against the live system (or mocked Qdrant/LLM for CI).

---

## Nuances discovered

1. **`create_payload_index` accepts raw strings** — `PayloadSchemaType` is a `str` Enum, so passing `"keyword"` directly works without conversion.

2. **`CompiledStateGraph` lives at `langgraph.graph.state.CompiledStateGraph`** — not directly importable from `langgraph.graph` in v1.1.10.

3. **FastEmbed CUDA warning is non-fatal** — falls back to CPU gracefully. The system can run without GPU for embeddings, just slower.

4. **Qdrant 400 vs 503 distinction** — a 400 (Wrong input) means Qdrant IS reachable but the data is wrong. A 503/ConnectionError means Qdrant is down. Important for debugging.

5. **`__init__.py` had existing edge_validator stubs** — these were preserved. The package now serves two purposes: old models/edge validation + new memory ingestion pipeline.

6. **Onnxruntime CUDA warnings in output are expected** — the env doesn't have CUDA libs for onnxruntime (different from PyTorch CUDA). Can add `providers=["CPUExecutionProvider"]` explicitly to suppress.
