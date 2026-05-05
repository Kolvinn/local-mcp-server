# Codebase Exploration Summary — Pre-Stage A1

Generated: 2026-05-05

## Existing Python Files in `src/`

| File | Purpose | Status for A1 |
|------|---------|---------------|
| `memory_service.py` (861 lines) | MCP memory server (Mem0 + Qdrant + Ollama) | **Unrelated** — uses Mem0 high-level API, not A1 models |
| `mcp_proxy_server.py` (152 lines) | MCP proxy/orchestrator with RBAC | **Unrelated** |
| `test_main.py` (1680 lines) | Unit tests for memory_service.py | **Unrelated** — mocks Mem0 entirely |
| `test_pipeline.py` (240 lines) | Raw Qdrant pipeline with Instructor | Has `MemoryMetadata` model but uses different categories |
| `instructor_test.py` (62 lines) | Scratch: Instructor + OpenCode Go | Ignore |
| `memtest1.py` (56 lines) | Scratch: Mem0 quick test | Ignore |
| `openai_test.py` (45 lines) | Scratch: API connectivity test | Ignore |
| `tests/test_goal_tools_live.py` (446 lines) | Live MCP integration tests | **Unrelated** |
| `tests/test_mcp_proxy.py` (189 lines) | MCP proxy test client | **Unrelated** |
| `tests/opencode-session-ping.py` (108 lines) | Session analysis tool | **Unrelated** |
| `util/agent_heartbeat.py` (196 lines) | Heartbeat daemon | **Unrelated** |

## Critical Observations

1. **No `src/memory/` directory exists** — Stage A1 must create it
2. **No `spec/` directory exists** — must be created for spec files
3. **No graph/edge validation models anywhere** — greenfield for A1
4. **Existing `MemoryMetadata`** in `test_pipeline.py` uses categories `procedural|declarative|objective` — these are different from the GraphRAG spec's `technical_fact|bug|decision|goal|code_symbol|documentation|exploration_finding|session_memory`. No conflict since A1 is in a separate module (`src/memory/`).
5. **Graphiti/FalkorDB** imported in `test_pipeline.py` but **not actually used** — commented out setup
6. **Test framework**: pytest >=8.3.4 already in `pyproject.toml`
7. **Pydantic**: >=2.10.6 already in `pyproject.toml`

## Imports Dependencies for A1

- `pydantic` — already in `pyproject.toml` (>=2.10.6)
- `json` — stdlib (for edge-contract.json loading)
- `pathlib` — stdlib (for edge-contract.json path resolution)
- `pytest` — already in `pyproject.toml` (>=8.3.4)

## Architecture for Stage A1

```
src/
├── memory/                    ← CREATE THIS DIRECTORY
│   ├── __init__.py            ← NEW: package init
│   ├── models.py              ← NEW: Category, Tag, NodeType, EdgeType enums
│   └── edge_validator.py      ← NEW: validate(s_label, rel, t_label) → bool
└── tests/
    └── test_models.py         ← NEW: pytest tests for A1

docs/rag-dev/
└── edge-contract.json         ← NEW: machine-readable adjacency matrix
```

## Environment for Implementers

- **Python:** `/home/dev/app/src/.venv/bin/python` (v3.14.4, venv managed by `uv` — `pip` is NOT in `.venv/bin/`, use `uv pip` if packages needed)
- **pytest:** `/home/dev/app/src/.venv/bin/pytest` (v9.0.3) — invoke via `cd /home/dev/app/src && .venv/bin/python -m pytest`
- **Working directory:** `/home/dev/app/src` — all imports assume `src/` is on the path (runs with `PYTHONPATH=/home/dev/app/src` or `cd src && python -m pytest`)
- **Package manager:** `uv` at `/home/dev/conda/bin/uv` — use for installing deps if needed (not needed for A1)
- **Import style:** Use **relative imports** within `src/memory/` (e.g. `from .models import ...`). Do NOT use absolute `from src.memory.*` imports — `src/` is NOT a package (no `src/__init__.py`).
- **pydantic:** v2.x already installed in venv

## Known Issues (pre-T5)

- `src/memory/__init__.py` line 3: uses `from src.memory.models` — MUST be `from .models`
- `src/memory/__init__.py` line 29: uses `from src.memory.edge_validator` — MUST be `from .edge_validator`
- `src/memory/edge_validator.py` lines 85, 148: uses `from src.memory.models` — MUST be `from .models`

## Files NOT to touch in A1

- `memory_service.py` — separate system, Mem0-based
- `test_main.py` — tests for memory_service.py
- `test_pipeline.py` — experimental Qdrant pipeline
- `pyproject.toml` — no new dependencies needed
