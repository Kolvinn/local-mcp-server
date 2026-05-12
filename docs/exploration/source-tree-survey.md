# Source Tree Survey

**Surveyed:** `src/` (excluding `src/agent_framework/`)
**Date:** 2026-05-12
**Purpose:** Identify entrypoints, packages, agent_framework dependencies, stale code, and __pycache__ dirs.

---

## Active Entrypoints

| File | Type | How Invoked | Description |
|------|------|-------------|-------------|
| `src/mcp_proxy_server.py` | MCP Server (FastMCP) | `python mcp_proxy_server.py` (has `if __name__ == "__main__"`) | Composite orchestrator that mounts downstream MCP servers (Redis, etc.). Runs on `MCP_PROXY_SERVER_PORT` (default 8000). Supports RBAC gatekeeping via `get_allowed_services` and `verify_access` tools. |
| `src/memory_service.py` | MCP Server (FastMCP) | `python memory_service.py` (has `if __name__ == "__main__"`) | Mem0-backed memory layer. Provides 9 MCP tools (`add_memory`, `search_memory`, `delete_memory`, `sync_metadata`, `list_projects`, `add_goal_node`, `search_goal_nodes`, `get_goal_tree`, `update_goal_node`, `delete_goal_node`). Runs on `MCP_MEM0_PORT` (default 8001). |
| `src/scripts/ingest_test.py` | CLI script | `python scripts/ingest_test.py <file_path>` (has `if __name__ == "__main__"`) | Ingests a file into Qdrant via the `memory` package. Calls `ingest_file()`, prints summary. Exit codes: 0 = success, 1 = error. |
| `src/tests/test_mcp_proxy.py` | CLI test client | `python tests/test_mcp_proxy.py [command]` (has `if __name__ == "__main__"`) | MCP JSON-RPC test client. Commands: init, ping, tools, resources, prompts, call. |
| `src/tests/test_goal_tools_live.py` | CLI integration test | `python tests/test_goal_tools_live.py` (has `if __name__ == "__main__"`) | Live end-to-end test for goal-tree MCP tools against running server. |
| `src/util/agent_heartbeat.py` | Daemon (incomplete) | `python util/agent_heartbeat.py` (has `if __name__ == "__main__"`, but only calls `fetch_pricing_data()`) | Half-implemented heartbeat daemon for OpenCode Go sessions. `run_daemon()` loop is defined but never called from `__main__`. |

## Packages

### `src/memory/` — GraphRAG Memory Manager

- **Purpose:** Ingestion pipeline for vector storage with classification, embedding, and graph validation.
- **Files (11):**
  - `__init__.py` — Package exports; forward-imports from all submodules with fallback stubs for edge_validator
  - `models.py` — Enums (Category, NodeType, EdgeType, TagDimension), TagRegistry singleton, register_edge_type/is_edge_type functions (284 lines)
  - `chunker.py` — Text chunker splitting on paragraph boundaries (94 lines)
  - `classifier.py` — Keyword-heuristic classifier for chunk category + tags (159 lines)
  - `embedder.py` — Dense (LiteLLM), sparse (FastEmbed), and late-interaction (FastEmbed) vector embedding (191 lines)
  - `graph.py` — LangGraph 3-node pipeline (validate_classify → build_payload → embed_ingest), with `ingest()` convenience wrapper (410 lines)
  - `ingest.py` — File ingestion pipeline (read → chunk → classify → embed → upsert to Qdrant) (199 lines)
  - `qdrant_client.py` — Qdrant singleton client, collection creation with named vectors (dense, sparse, multi), upsert (196 lines)
  - `edge_validator.py` — Edge triple validation against edge-contract.json + runtime registration (202 lines)
  - `sparse_embed.py` — Standalone test script (NOT imported by package, see Stale/Dead Code)
  - `taxonomy_loader.py` — Load taxonomy-schema.json, validate classifications, extract payload indexes (111 lines)
- **Dependencies:** `langgraph`, `litellm`, `qdrant-client`, `fastembed`, `fastembed-gpu`, `pydantic`, `httpx`
- **agent_framework dependency:** NONE

### `src/scripts/` — CLI Scripts

- **Files:** `ingest_test.py` (1 file)
- **Purpose:** CLI entrypoint for the memory ingestion pipeline.
- **agent_framework dependency:** NONE

### `src/tests/` — Test Files

- **Files (5):**
  - `test_main.py` — Comprehensive unit tests for `memory_service.py` (filter construction, tool logic, server startup) (1680 lines)
  - `test_models.py` — Unit tests for `memory.models` and `memory.edge_validator` (AC acceptance criteria) (534 lines)
  - `test_mcp_proxy.py` — MCP protocol test client (189 lines)
  - `test_goal_tools_live.py` — Live integration tests for goal-tree tools (446 lines)
  - `test_langchain.py` — LangChain/Deep Agents prototype test (120 lines)
  - `opencode-session-ping.py` — Standalone SQLite analysis script (108 lines)
- **agent_framework dependency:** NONE

### `src/util/` — Utilities

- **Files:** `agent_heartbeat.py`, `delete_qdrant_cols.sh`
- **Purpose:** OpenCode Go heartbeat daemon, Qdrant cleanup script
- **agent_framework dependency:** NONE

### Standalone Files (no package membership)

| File | Description |
|------|-------------|
| `src/hybrid_embed_test.py` | Qdrant hybrid search test (dense/sparse/late-interaction). Early prototype. Partially refactored into `memory/embedder.py`. |
| `src/instructor_test.py` | Instructor library test with OpenCode Go. Has `async def process_and_store()` but no `__main__`. |
| `src/memtest1.py` | Quick Mem0 test script. Calls `load()` at module level. |
| `src/openai_test.py` | OpenAI/OpenCode Go connection test. Calls API at module level. |
| `src/test_pipeline.py` | Early pipeline prototype (Graphiti + Qdrant + Ollama). Has `if __name__ == "__main__"`. |

---

## Files Dependent on agent_framework (will break)

**NONE** found.

The `grep` for `agent_framework` across all `.py` files under `src/` (excluding `src/agent_framework/` itself) returned **zero matches**. All 18 references to `agent_framework` are internal to the `src/agent_framework/` package itself (its own imports).

Deleting `src/agent_framework/` will **not** break any other files in `src/`.

---

## Stale / Dead Code

| File | Why It Appears Unused |
|------|-----------------------|
| `src/memory/sparse_embed.py` | Standalone script that runs at module level (no function wrapping). Not imported by any package. Appears to be an early SPLADE embedding exploration. |
| `src/hybrid_embed_test.py` | Standalone test for Qdrant hybrid search. Lines 61-116 were refactored into `memory/embedder.py` (noted in embedder.py line 5). The script runs `create_points()` and `hybrid_search()` at module level. |
| `src/memtest1.py` | Quick Mem0 connectivity test. Runs at module level (`load()` called on line 56). Not imported by any package. |
| `src/openai_test.py` | OpenAI connection test. Runs API call at module level. Not imported. |
| `src/instructor_test.py` | Instructor library test with `async def process_and_store()`. Not imported, no `__main__`. |
| `src/test_pipeline.py` | Early pipeline prototype (Graphiti + Qdrant). Has `__main__` but relies on FalkorDB driver pointing to "optimistic_benz". Standalone test. |
| `src/tests/opencode-session-ping.py` | Standalone script that reads OpenCode SQLite DB directly. Not imported by any test runner. |
| `src/util/agent_heartbeat.py` | Has `run_daemon()` loop defined but **never called**. The `__main__` block only calls `fetch_pricing_data()` and exits. Half-implemented. |

---

## __pycache__ Directories

```
src/__pycache__/
src/memory/__pycache__/
src/scripts/__pycache__/
src/tests/__pycache__/
```

---

## Summary

- **Active services:** `mcp_proxy_server.py` (port 8000) and `memory_service.py` (port 8001), both FastMCP-based.
- **Main package:** `src/memory/` — fully self-contained GraphRAG ingestion pipeline.
- **agent_framework impact:** Zero — no files outside `agent_framework/` import from it.
- **Dead code:** ~8 files that are standalone tests or half-implemented utilities not imported by anything.
- **__pycache__ cleanup:** 4 directories that can be safely deleted.
