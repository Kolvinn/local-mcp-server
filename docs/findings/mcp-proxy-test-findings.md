# MCP Proxy Connectivity Test — Findings

## Purpose

Test the end-to-end MCP proxy pipeline: ingest (`add_memory`), search (`search_memory`), and remove (`delete_memory`) via the proxy at `mcp_proxy_server.py`.

## Architecture

```
opencode (client)
  └─> mcp_proxy_server.py  (FastMCP, port 8000)
        ├── gatekeeper tools:  get_allowed_services(), verify_access()     [WORKING]
        ├── proxy: sequential-thinking  (bunx)                           [WORKING]
        └── proxy: memory  (python ./src/main.py)
              └─ Mem0 v2.0.0  ── Qdrant (docker, qdrant:6333)
                              └─ Ollama (docker, ollama:11434)
                                  - nomic-embed-text  (768-dim)
                                  - llama3.1:8b
```

## What Works

| Component | Status | Notes |
|---|---|---|
| Gatekeeper RBAC | WORKING | `get_allowed_services` and `verify_access` correctly enforce agent roles |
| Sequential Thinking proxy | WORKING | Mounted via bunx, responds correctly |
| Proxy mounts | WORKING | Both downstream servers mount without error |

### Gatekeeper Role Matrix

| Agent ID | Roles | Tools Allowed |
|---|---|---|
| `agent_alpha` | sequential_thinking, memory_read | 5 tools |
| `agent_admin` | sequential_thinking, memory_read, memory_write | 11 tools |
| `guest` | (none) | 0 tools |
| (any other) | — | Error: "Agent ID not recognized" |

## What Blocks Memory Testing

### Bug 1: Vector Dimension Mismatch

**Blocks:** `add_memory`, and all write paths.

**Error:**
```
Vector dimension error: expected dim: 1536, got 768
```

**Root cause:**
The Qdrant `mem0` collection was created by a prior configuration using a 1536-dim embedding model (e.g., OpenAI text-embedding-ada-002). The current `.env` config uses `nomic-embed-text` which outputs 768-dim vectors. The collection has **0 points** (empty) but its vector config is locked to 1536.

**Fix:**
1. `curl -X DELETE http://qdrant:6333/collections/mem0`
2. Restart the memory server (`main.py`) — Mem0 recreates the collection with the correct dimension on first write.

---

### Bug 2: Mem0 v2.0.0 API Breakage — `user_id` rejected by search/get_all

**Blocks:** `search_memory`, `list_projects`

**Error:**
```
Top-level entity parameters frozenset({'user_id'}) are not supported in search().
Use filters={'user_id': '...'} instead.
```

**Root cause:**
Mem0 v2.0.0 removed `user_id` as a top-level parameter from `search()` and `get_all()`. The code in `src/main.py` passes it as a kwarg, which is now rejected.

**Actual API signatures (mem0 v2.0.0):**
```
add:      (self, messages, *, user_id=None, agent_id=None, run_id=None, metadata=None, infer=True, ...)
search:   (self, query, *, top_k=20, filters=None, threshold=0.1, rerank=False, **kwargs)     ← NO user_id
get_all:  (self, *, filters=None, top_k=20, **kwargs)                                         ← NO user_id
delete:   (self, memory_id)
```

**Affected code locations in `src/main.py`:**

| Line | Current (broken) | Fix |
|---|---|---|
| 391-396 | `search(query, filters, user_id=..., limit=...)` | Move `user_id` into `filters` dict |
| 510 | `get_all(user_id=..., filters={}, limit=100)` | Move `user_id` into `filters` dict |
| 513-517 | `search(query="*", filters={}, user_id=..., limit=100)` | Move `user_id` into `filters` dict |

Note: `add()` at line 352-357 still accepts `user_id` as a top-level param — it is NOT affected by this bug. But it is blocked by Bug 1.

## Environment

| Component | Value |
|---|---|
| Python runtime | `python3.14` from conda env `dev1` (`/home/dev/conda/envs/dev1/`) |
| mem0 version | 2.0.0 |
| Qdrant | Docker, host `qdrant:6333`, collection `mem0` (0 points, dim=1536) |
| Ollama | Docker, host `ollama:11434`, models: `nomic-embed-text` + `llama3.1:8b` |
| Proxy port | 8000 (streamable-http) |

## Data State

No test data was written. The Qdrant `mem0` collection has 0 points. Nothing to clean up.

## Suggestions for Workflow Improvement

1. **Add a `healthcheck` tool to the proxy** — pings each downstream service and reports configuration mismatches (collection dim vs. model dim) at discovery time rather than at write time.
2. **Pin mem0 version in `requirements.txt`** — the code was written against an older API. Pinning would prevent silent breakage on upgrade.
3. **Add a `verify_env` startup check in `main.py`** — validate Qdrant collection dimensions against the configured embedding model before accepting requests.
4. **Inject `user_id` into `filters`** for search/get_all — Mem0 v2 moved user/agent/run scoping into the filters dict for non-write operations.
