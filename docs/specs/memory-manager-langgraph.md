# Memory Manager — LangGraph Pseudocode Spec

**Source brief:** `docs/briefs/memory-manager-langgraph.md`
**State diagram:** `docs/diagrams/memory-manager-state.mmd`
**Target:** `src/memory/` (5 files: `__init__.py`, `graph.py`, `embedder.py`, `qdrant_client.py`, `taxonomy_loader.py`)

---

## 1. Data Structures

```
MODEL: MemoryManagerInput (Pydantic BaseModel)
    content: str                                          # required, non-empty
    category_type: Optional[Literal["knowledge","objective","learning","thought"]]
    category: Optional[str]                               # subcategory value
    tags: list[str] = []                                  # cross-cutting labels
    source: str                                           # required, non-empty

MODEL: MemoryManagerOutput (Pydantic BaseModel)
    chunk_id: str | None                                  # None on error
    ingested_at: str | None                               # ISO8601, None on error
    error: str | None                                     # None on success

MODEL: TaxonomyClassification (Pydantic BaseModel)
    category_type: Literal["knowledge","objective","learning","thought"]
    category: str
    tags: list[str]
    key_words: list[str]

MODEL: QdrantPayload (Pydantic BaseModel)
    chunk_id: str
    graph_node_id: str | None                             # always None for MVP
    category_type: str
    category: str
    tags: list[str]
    key_words: list[str]
    content: str
    summary: str | None                                   # always None for MVP
    source: str
    status: str                                           # always "active"
    version: int                                          # always 1
    created_at: str                                       # ISO8601
    updated_at: str                                       # ISO8601

STATE SCHEMA (LangGraph TypedDict):
    MemoryManagerState(TypedDict):
        content: str
        category_type: str | None
        category: str | None
        tags: list[str]
        source: str
        key_words: list[str]
        chunk_id: str | None
        payload: dict | None
        point_struct: PointStruct | None                  # qdrant_client.models.PointStruct
        ingested_at: str | None
        error: str | None

ENUM: EmbedType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    LATE_INTERACTION = "multi"
```

---

## 2. Module: `taxonomy_loader.py`

```
FUNCTION: load_taxonomy() -> dict
    PURPOSE: Load taxonomy-schema.json from disk, return parsed dict.
    BEHAVIOR:
        1. Read docs/rag-dev/taxonomy-schema.json from project root
        2. Parse as JSON
        3. Cache in module-level _taxonomy_cache for subsequent calls
        4. Return the parsed dict
    ERROR CONDITIONS:
        - FileNotFoundError if taxonomy-schema.json missing
        - json.JSONDecodeError if file is malformed
    EDGE CASES:
        - First call reads file; subsequent calls return cached dict (no re-read)

FUNCTION: validate_classification(taxonomy: dict, category_type: str, category: str, tags: list[str]) -> bool
    PURPOSE: Check that category_type, category, and each tag exist in the taxonomy.
    BEHAVIOR:
        1. Assert category_type is in taxonomy["category_types"] list
        2. Assert category is a key in taxonomy["categories"][category_type]["subcats"]
        3. For each tag in tags:
           Assert tag is a key in taxonomy["categories"][category_type]["tags"]
        4. Return True if all assertions pass; raise ValueError with detail otherwise
    ERROR CONDITIONS:
        - ValueError("Unknown category_type: {value}") if type not in schema
        - ValueError("Unknown category: {value} for type {type}") if subcategory unknown
        - ValueError("Unknown tag: {value} for type {type}") if any tag unknown
    EDGE CASES:
        - Empty tags list is valid (passes without checking)

FUNCTION: get_payload_indexes(taxonomy: dict) -> list[tuple[str, str]]
    PURPOSE: Extract (field_name, index_type) pairs from taxonomy payload_indexes.
    BEHAVIOR:
        1. Read taxonomy["payload_indexes"]
        2. Return list of (field_name, field_schema) tuples
    EXAMPLE OUTPUT: [("category_type","keyword"), ("category","keyword"), ("tags","keyword_list"), ...]
```

---

## 3. Module: `embedder.py`

    REFACTORED FROM: src/hybrid_embed_test.py lines 61-116 (Embedder class + EmbedType enum)

```
CLASS: Embedder
    PURPOSE: Produce dense, sparse, and late-interaction vectors for a given text.
    
    CONFIG (from environment):
        LITE_LLM_URL: str         (default "http://litellm:4000")
        LITE_LLM_API_KEY: str     (default "sk-1234")
        DENSE_MODEL: str          (default "openai/nomic-embed")
        SPARSE_MODEL: str         (default "prithivida/Splade_PP_en_v1")
        LI_MODEL: str             (default "answerdotai/answerai-colbert-small-v1")
        DIM_SIZE: int = 768
        LI_DIM_SIZE: int = 128

    INTERNAL STATE (lazy-init, module-level singletons):
        _sparse_model: SparseTextEmbedding | None        # FastEmbed, CUDA=false
        _li_model: LateInteractionTextEmbedding | None    # FastEmbed

    METHOD: embed(text: str, type: EmbedType) -> Vector | SparseVector | list[list[float]]
        BEHAVIOR:
            IF type == DENSE:
                1. Call litellm.embedding() with api_base, api_key, model, input=text
                2. Return response.data[0]["embedding"] (list[float], length 768)
            IF type == SPARSE:
                1. Lazy-init _sparse_model if None
                2. Call _sparse_model.embed([text]), take first result
                3. Return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())
            IF type == LATE_INTERACTION:
                1. Lazy-init _li_model if None
                2. Call _li_model.embed([text]), take first result
                3. Return result.tolist() (list[list[float]])
        ERROR CONDITIONS:
            - ConnectionError if LiteLLM unreachable (dense path)
            - RuntimeError if FastEmbed model fails to load (sparse/LI paths)
            - IndexError if embedding response has no data[0]
        EDGE CASES:
            - Empty string input: let the embedding model handle it (may produce zero vectors)

FUNCTION: get_embedder() -> Embedder
    PURPOSE: Return module-level singleton Embedder instance. Lazy-init on first call.
```

---

## 4. Module: `qdrant_client.py`

```
CONSTANTS (from environment):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "memory_chunks"
    DENSE_DIM: int = 768
    LI_DIM: int = 128

FUNCTION: get_qdrant_client() -> QdrantClient
    PURPOSE: Return module-level singleton QdrantClient. Host/port from env.

FUNCTION: ensure_collection_exists() -> None
    PURPOSE: Create memory_chunks collection if it doesn't already exist.
    BEHAVIOR:
        1. If client.collection_exists(COLLECTION_NAME): return
        2. Create collection with:
           - Named vector "dense": size=DENSE_DIM, distance=COSINE
           - Named vector "multi": size=LI_DIM, distance=COSINE,
             multivector_config=MultiVectorConfig(comparator=MAX_SIM),
             hnsw_config=HnswConfigDiff(m=0)     # HNSW disabled for multivectors
           - Sparse vector "sparse": modifier=IDF
        3. Create payload indexes from taxonomy_loader.get_payload_indexes():
           FOR EACH (field_name, index_type) in indexes:
               client.create_payload_index(COLLECTION_NAME, field_name, index_type)
    ERROR CONDITIONS:
        - ConnectionError if Qdrant unreachable
        - RuntimeError if collection creation fails (propagate Qdrant error)
    EDGE CASES:
        - Collection already exists: no-op (idempotent)
        - Payload index already exists: catch and ignore duplicate index error

FUNCTION: upsert_point(point: PointStruct) -> str
    PURPOSE: Upsert a single PointStruct into the collection. Return the chunk_id.
    BEHAVIOR:
        1. client.upsert(COLLECTION_NAME, points=[point])
        2. Return point.payload["chunk_id"] as confirmation
    ERROR CONDITIONS:
        - ConnectionError if Qdrant unreachable
        - ValueError if point has no payload or no chunk_id in payload
        - RuntimeError on upsert rejection (propagate Qdrant error)
    EDGE CASES:
        - Re-upsert with same chunk_id: overwrites existing point (version bump handled upstream)
```

---

## 5. Module: `graph.py`

```
FUNCTION: build_graph() -> CompiledStateGraph
    PURPOSE: Construct, wire, and compile the 3-node StateGraph. Return compiled graph.

    GRAPH STRUCTURE:
        START -> validate_classify -> build_payload -> embed_ingest -> END

    ── NODE 1: validate_classify ──

    FUNCTION: validate_classify_node(state: MemoryManagerState) -> dict
        PURPOSE: Ensure category_type, category, tags, and key_words are present and valid.
        BEHAVIOR:
            1. taxonomy = taxonomy_loader.load_taxonomy()
            2. IF state["category_type"] is not None AND state["category"] is not None:
                2a. taxonomy_loader.validate_classification(
                       taxonomy, state["category_type"], state["category"], state["tags"])
                2b. Return {"category_type": state["category_type"],
                            "category": state["category"],
                            "tags": state["tags"],
                            "key_words": state.get("key_words", [])}
            3. ELSE (classification incomplete):
                3a. Build system prompt:
                    "You are a text classifier. Classify this text using the taxonomy below.
                     Return JSON with keys: category_type, category, tags, key_words.
                     Taxonomy: {json.dumps(taxonomy["categories"])}
                     Text: {state['content']}"
                3b. Call deepseek-flash LLM with system prompt, request structured JSON output
                3c. Parse LLM response into TaxonomyClassification model
                3d. taxonomy_loader.validate_classification(
                       taxonomy, result.category_type, result.category, result.tags)
                3e. Return {"category_type": result.category_type,
                            "category": result.category,
                            "tags": result.tags,
                            "key_words": result.key_words}
        ERROR CONDITIONS:
            - ValueError: classification invalid (bubble up — caught by caller)
            - RuntimeError: LLM call fails or returns unparseable JSON
              → retry ONCE with error injected into prompt
              → if retry fails: return {"error": "LLM classification failed: {details}"}
        SIDE EFFECTS: None (read-only; taxonomy is cached after first load)
        EDGE CASES:
            - tags is empty list: valid (no tags assigned)
            - key_words is empty list: valid (no keywords extracted)
            - LLM returns valid JSON but with unknown values: rejected by validate_classification

    ── NODE 2: build_payload ──

    FUNCTION: build_payload_node(state: MemoryManagerState) -> dict
        PURPOSE: Assemble the QdrantPayload and wrap into a PointStruct (no vectors yet).
        BEHAVIOR:
            1. chunk_id = str(uuid.uuid4())
            2. now = datetime.utcnow().isoformat() + "Z"
            3. payload = QdrantPayload(
                   chunk_id=chunk_id,
                   graph_node_id=None,
                   category_type=state["category_type"],
                   category=state["category"],
                   tags=state["tags"],
                   key_words=state["key_words"],
                   content=state["content"],
                   summary=None,
                   source=state["source"],
                   status="active",
                   version=1,
                   created_at=now,
                   updated_at=now,
               )
            4. point = PointStruct(id=chunk_id, vector={}, payload=payload.model_dump())
            5. Return {"chunk_id": chunk_id, "payload": payload.model_dump(), "point_struct": point}
        ERROR CONDITIONS:
            - No expected errors (pure data assembly; all inputs validated by node 1)
        SIDE EFFECTS: None (no I/O)
        EDGE CASES:
            - UUID collision: astronomically unlikely; not handled

    ── NODE 3: embed_ingest ──

    FUNCTION: embed_ingest_node(state: MemoryManagerState) -> dict
        PURPOSE: Generate all three vectors, attach to PointStruct, upsert into Qdrant.
        BEHAVIOR:
            1. embedder = embedder_module.get_embedder()
            2. qdrant_client.ensure_collection_exists()
            3. point = state["point_struct"]
            4. point.vector["dense"] = embedder.embed(state["content"], EmbedType.DENSE)
            5. point.vector["sparse"] = embedder.embed(state["content"], EmbedType.SPARSE)
            6. point.vector["multi"] = embedder.embed(state["content"], EmbedType.LATE_INTERACTION)
            7. qdrant_client.upsert_point(point)
            8. ingested_at = datetime.utcnow().isoformat() + "Z"
            9. Return {"ingested_at": ingested_at}
        ERROR CONDITIONS:
            - ConnectionError if LiteLLM or Qdrant unreachable: return {"error": str(e)}
            - RuntimeError if embedding generation fails: return {"error": "Embedding failed: {details}"}
            - RuntimeError if upsert fails: return {"error": "Upsert failed: {details}"}
        SIDE EFFECTS:
            - Writes to Qdrant (upserts one point into memory_chunks collection)
            - First call triggers collection creation (payload indexes)
        EDGE CASES:
            - Qdrant collection doesn't exist yet: ensure_collection_exists() creates it
            - Embedding model not yet loaded: lazy-init in Embedder handles it

    ── GRAPH ASSEMBLY ──

    FUNCTION: build_graph() -> CompiledStateGraph
        BEHAVIOR:
            1. builder = StateGraph(MemoryManagerState)
            2. builder.add_node("validate_classify", validate_classify_node)
            3. builder.add_node("build_payload", build_payload_node)
            4. builder.add_node("embed_ingest", embed_ingest_node)
            5. builder.add_edge(START, "validate_classify")
            6. builder.add_edge("validate_classify", "build_payload")
            7. builder.add_edge("build_payload", "embed_ingest")
            8. builder.add_edge("embed_ingest", END)
            9. RETURN builder.compile()
        NOTE: No conditional edges. Error nodes return error in state dict; caller checks
              result["error"] after invoke(). The graph always reaches END regardless of errors.

    ── SHORTCUT INVOKE ──

    FUNCTION: ingest(content: str, source: str,
                     category_type: str | None = None,
                     category: str | None = None,
                     tags: list[str] | None = None) -> MemoryManagerOutput
        PURPOSE: Convenience wrapper — build input, invoke graph, return output.
        BEHAVIOR:
            1. input_state = MemoryManagerInput(
                   content=content, source=source,
                   category_type=category_type, category=category,
                   tags=tags or [])
            2. graph = build_graph()       # compiled once, reused via module-level cache
            3. result = graph.invoke(input_state.model_dump())
            4. RETURN MemoryManagerOutput(
                   chunk_id=result.get("chunk_id"),
                   ingested_at=result.get("ingested_at"),
                   error=result.get("error"))
        EDGE CASES:
            - Empty content string: rejected by MemoryManagerInput validation (min_length=1)
```

---

## 6. Module: `__init__.py`

```
EXPORTS:
    from .graph import build_graph, ingest
    from .embedder import Embedder, EmbedType, get_embedder
    from .qdrant_client import get_qdrant_client, ensure_collection_exists, upsert_point
    from .taxonomy_loader import load_taxonomy, validate_classification, get_payload_indexes

PACKAGE-LEVEL:
    _graph: CompiledStateGraph | None = None   # cached compiled graph

FUNCTION: get_graph() -> CompiledStateGraph
    PURPOSE: Return module-level cached graph, building on first call. Idempotent.
```

---

## 7. Error Handling Strategy

```
ALL NODES follow the same pattern:
    - Return {"error": str} on failure (never raise from within a node)
    - Caller checks result["error"] after invoke()
    - Graph always reaches END (no unrecoverable halts)

ERROR CLASS HIERARCHY:
    ClassificationError(ValueError)     — taxonomy validation failures
    LLMError(RuntimeError)              — deepseek-flash unreachable or unparseable
    QdrantError(ConnectionError)        — Qdrant unreachable or upsert rejected
    EmbeddingError(RuntimeError)        — LiteLLM or FastEmbed failures

RETRY STRATEGY:
    - validate_classify: LLM call retried ONCE on parse failure (not on validation failure)
    - embed_ingest: NO retry for embedding/upsert (let caller decide)
```

---

## 8. Test Plan (locations, not implementation)

```
FILE: src/tests/test_taxonomy_loader.py
    - test_load_taxonomy_returns_valid_dict()
    - test_load_taxonomy_caches_on_second_call()
    - test_validate_classification_accepts_valid_input()
    - test_validate_classification_rejects_unknown_category_type()
    - test_validate_classification_rejects_unknown_category()
    - test_validate_classification_rejects_unknown_tag()
    - test_validate_classification_accepts_empty_tags()

FILE: src/tests/test_embedder.py
    - test_embed_dense_returns_768_dim_vector()
    - test_embed_sparse_returns_sparse_vector()
    - test_embed_late_interaction_returns_2d_list()
    - test_get_embedder_returns_singleton()

FILE: src/tests/test_graph.py
    - test_ingest_full_classification_skips_llm(mocker)
    - test_ingest_partial_classification_calls_llm(mocker)
    - test_ingest_invalid_classification_returns_error(mocker)
    - test_ingest_embedding_failure_returns_error(mocker)
    - test_ingest_qdrant_failure_returns_error(mocker)
    - test_ingest_empty_content_rejected()
    - test_ingest_returns_chunk_id_on_success(mocker)
    - test_graph_compile_has_three_nodes()

RUN: src/.venv/bin/python -m pytest src/tests/ -v
```

---

## 9. Implementation Notes for Implementer

```
DO:
    - Refactor Embedder class from src/hybrid_embed_test.py lines 61-116
    - Use relative imports within src/memory/ (e.g., from .taxonomy_loader import load_taxonomy)
    - Read all config from environment variables with defaults
    - Use Pydantic v2 model_dump() (not .dict())
    - Type hint ALL function signatures

DO NOT:
    - Do NOT add __init__.py to src/ — src/memory/__init__.py is the package boundary
    - Do NOT import from src.* — src/ is not a Python package
    - Do NOT hardcode model names, hostnames, ports, or API keys
    - Do NOT implement chunking, Memgraph, Redis, HTTP endpoints, or batch ingestion
    - Do NOT add authentication or multi-tenancy
    - Do NOT use npx — bunx for JS tooling if needed

FILES TO READ:
    - docs/rag-dev/taxonomy-schema.json (taxonomy source of truth)
    - src/hybrid_embed_test.py (refactoring source for embedder)
    - docs/context/conventions.md (import rules, naming, test commands)
    - docs/context/stack.md (env vars, framework versions)
    - docs/context/constraints.md (VRAM limits, no auth, no npx)

FILES TO WRITE:
    - src/memory/__init__.py
    - src/memory/taxonomy_loader.py
    - src/memory/embedder.py
    - src/memory/qdrant_client.py
    - src/memory/graph.py
```

(End of spec — 350 lines)
