# Key Facts

Project configuration, constants, and frequently-needed **non-sensitive** information. Organize by category using bullet lists.

---

## ⚠️ SECURITY WARNING

**NEVER store passwords, API keys, or sensitive credentials in this file.** Use `.env` files (gitignored) or secrets managers.

---

## Project Identity

- **Project**: local-mcp-server
- **Purpose**: MCP server providing a local AI memory layer using Mem0, Qdrant, and Ollama
- **Agent Context**: OpenCode (NOT Roo Code — "roo_agent" user_id is stale)
- **Repository**: `/home/dev/app`

## Runtime Stack

- **Language (Primary)**: Python 3 (conda env `dev1`)
- **Language (Secondary)**: TypeScript/Bun — placeholder only, `src/index.ts` is dead code
- **MCP Framework**: FastMCP 3.2.4+
- **Web Framework**: FastAPI 0.136+
- **ASGI Server**: Uvicorn 0.44+
- **HTTP Client**: httpx 0.28+
- **Memory SDK**: mem0ai (latest, in pyproject.toml, wired in src/main.py via in-process import)
- **Env Vars**: python-dotenv 1.2+ (no .env file currently exists — env set via shell/Docker)
- **Package Manager**: uv (installed via conda-forge, uses `uv pip install pyproject.toml --system`)
- **JS Runtime**: Bun (available via conda, unused for core logic)

## Infrastructure

- **Base Image**: `framework-opencode:latest` — custom, conda-based. NOT on Docker Hub. Must be pre-built.
- **Conda Environment**: `dev1` at `/home/dev/conda/envs/dev1`
- **Container Name**: `mcp-server`
- **Container Mount**: `/home/dev/app` → copied into container at build time (COPY --chown=dev:dev ./dev/mcp-server/)
- **Network**: `internal-net` (external Docker network, shared by all containers)
- **Reverse Proxy**: Traefik (labels-based routing)
- **User**: `dev:1000:1000`
- **Access Model**: Single user only. No auth, no public exposure. User connects directly.

## Port Reference

| Service | Internal Port | Notes |
|---------|---------------|-------|
| mcp-server | **8000** (target serving port) | Proxy serves here, memory service attached behind |
| mcp-memory-service | 8000 | Internal memory MCP server (src/main.py) |
| Traefik label | 6274 | Vestigial, was for MCP Inspector UI on host. No longer used. |
| Qdrant | 6333 | User-managed, external to this repo |
| Ollama | 11434 | User-managed, external to this repo |

## External Infrastructure (User-Managed)

- **Qdrant**: Vector store. User ensures it's running at `QDRANT_HOST`:`QDRANT_PORT`. Not in this repo's compose.
- **Ollama**: LLM + embeddings. User ensures it's running at `OLLAMA_URL`. Currently only `nomic-embed-text` is pulled. LLM model (`llama3.1:8b`) needs to be pulled before `add_memory` with `infer=True` will work. Not in this repo's compose.

## Environment Variables

- `QDRANT_HOST` — Qdrant server hostname (default: `qdrant`)
- `QDRANT_PORT` — Qdrant server port (default: `6333`)
- `OLLAMA_URL` — Ollama server URL (default: `http://ollama:11434`)
- `EMBEDDING_MODEL` — Embedding model (default: `nomic-embed-text`)
- `LLM_MODEL` — LLM for fact extraction + compact_session (default: `llama3.1:8b`). **Must be pulled in Ollama before use.**
- `AGENT_ID` — user_id for Mem0, who created the memory (default: `default_agent`)
- `STALENESS_WINDOW_DAYS` — Days before memory flagged stale (default: `30`)
- `HOST` — Server bind address (default: `0.0.0.0`)
- `PORT` — Server port (default: `8000`, fixes 8001 misalignment)
- `MEMORY_CONTEXT_BASE` — Base directory for .memory-context.yaml writes (default: `/home/dev/app`)

## V0 MCP Tools (5)

- `add_memory` — Store fact + metadata (tags, project_id, source_user, related_files, source_path, validated_at). **Pending: adding `infer` param (ADR-020)**
- `search_memory` — Semantic search + metadata filtering (tags, project_id, source_user) + threshold
- `delete_memory` — Remove by ID
- `sync_metadata` — Create/update `.memory-context.yaml` at a path (with path validation)
- `list_projects` — List distinct project_ids from stored memories

## Infer Parameter (ADR-020)

- `add_memory` current: `infer=True` hardcoded — every call triggers local LLM fact extraction
- `add_memory` pending: `infer` as optional boolean param (default `True`)
- `infer=True` → LLM extracts structured facts from raw content. Automatic dedup via Mem0. Heavy VRAM.
- `infer=False` → Agent pre-extracts facts, server only embeds + stores. No dedup. Lightweight.
- **Open question**: Should default change to `False` since agents are primary callers? Pending user decision.
- **Architecture implication**: If default becomes `False`, local LLM model becomes optional (only needed for bulk inference scripts), cutting VRAM from ~8GB to ~300MB

## Local Metadata Spec

- File: `.memory-context.yaml` — auto-discovered per directory, cascades like .gitignore
- Fields: `version`, `project_id`, `tags`, `scope_summary`
- No memory_ids — shared vocabulary coupling only (tags, project_id)

## Memory Scoping (3 dimensions)

- `user_id` — who created (AGENT_ID env var)
- `project_id` — what project (from `.memory-context.yaml`)
- `source_user` — who it's about (optional, for business partners/clients)

## Test Infrastructure

- **Unit tests**: `src/test_main.py` — 50 mock tests, no live infrastructure. Pass.
- **Live ingestion tests**: `tests/integration/test_live_ingestion.py` — 11 tests, real workflow, live Qdrant + Ollama
- **Test runner**: Inside Docker on `internal-net`. httpx POST to proxy endpoint.
- **HTTP target**: `http://mcp-server:PORT/mcp` — proxy mounts memory service backend. Tests hit proxy, proxy forwards to memory service.
- **Test cleanup**: Delete Qdrant collection after test suite completes (all test memories wiped).
- **Test isolation**: `AGENT_ID=test_ingest_{uuid}` for live tests, separate from production data.
- **Real workflow**: All 11 tests use real Mem0 client, real Qdrant, real Ollama (nomic-embed-text + llama3.1:8b). No mocks.
- **Dependencies**: Must run `uv pip install pyproject.toml --system` in `dev1` conda env before testing.
- **No new envs**: Do not create new environments within the project folder. Use existing `dev1`.

## V2 Deferred

- `cleanup_stale` tool, `check_drift` tool, reingest pipeline, subagent workers

## Fixed Constraints

- **Hardware**: RTX 3080 (10GB VRAM max), 32GB RAM max
- **No npx**: Use `bunx` or `conda` instead
- **No Node.js**: This environment uses conda + bun
- **No auth/multi-tenancy**: Single user access model only
- **No healthchecks**: Not a priority right now

## Agent Team (v2 — ADR-023)

### Agents

| Agent | Mode | Model | Role |
|-------|------|-------|------|
| **Orchestrator** | primary | deepseek-v4-pro | Sole user contact. Owns goals, workflow state, delegation, 4 approval gates. Never designs, codes, explores, reviews. |
| **System Thinker** | all (spawnable) | kimi-k2.5 | Template-based domain designer. Loads skills per delegation. Produces options (wide) and pseudocode specs (deep). Records learnings. |
| **Implementer** | subagent | kimi-k2.5 | Translates pseudocode specs → production code. No design decisions. Reads `docs/context/` for project conventions. |
| **Reviewer** | subagent | kimi-k2.5 | Read-only. Verifies code against pseudocode spec. Classifies: Blocker/Major/Minor/Suggestion. Writes review to file. |
| **Explorer** | subagent | deepseek-v4-flash | Read-only. File search + structural analysis (dependency graphs, call chains). Writes to `docs/exploration/`, returns only `complete`/`error`. |

### Key Protocols

**Transparency Protocol:** Every agent writes full output to file (`docs/briefs/`, `docs/specs/`, `docs/reviews/`, `docs/exploration/`), passes condensed summary to consumer. Orchestrator never reads raw agent output — summaries only.

**File Access Protocol (Orchestrator):** Uses `head -c 5000 <file>` before reading directly. If output = 5000 bytes, delegates to Explorer. `docs/context/` files read directly. Source code always delegated. User instruction overrides threshold.

**Pseudocode Handoff:** System Thinker → Implementer via `docs/specs/{name}.md`. Implementer translates, doesn't interpret. Reviewer verifies structural compliance.

**Approval Gates:** G1 (approach) → G2 (spec) → G3 (code) → G4 (review). Lightweight confirmations. Trivial changes can skip intermediate gates with user consent. Gate 4 never skipped.

**Three-Tier Context:** Tier 1 (methodology, baked in prompt), Tier 2 (domain, `docs/context/`), Tier 3 (task, delegation prompt). All agents are project-agnostic.

**Evolution:** Orchestrator collects session ratings → `docs/ratings/`. System Thinker records learnings → `docs/learnings/{domain}/`. Accumulated data feeds improvement runs.

### Agent Config Files

- `opencode.jsonc` — 5 agents: orchestrator, system_thinker, implementer, reviewer, explorer
- `prompts/orchestrator.md` — Entry agent: goals, gates, delegation, file access protocol
- `prompts/system_thinker.md` — Spawnable template: options → pseudocode, skill loading, learning recording
- `prompts/implementer.md` — Project-agnostic translator: reads context + spec, writes code
- `prompts/reviewer.md` — Pseudocode compliance verification, writes review to file
- `prompts/explorer.md` — Structural analysis tools, file-only output protocol

### Removed Agents

- `coordinator.md`, `product_owner.md` — Superseded by Orchestrator
- `expert.md` — Superseded by System Thinker
- `agentic_architect.md`, `agent-creator.md`, `agent_team.md` — Removed

### File Convention Map

```
docs/
├── context/              ← Tier 2: project-specific (stack, conventions, constraints, services)
├── briefs/               ← System Thinker: option analyses (wide phase)
├── specs/                ← System Thinker: pseudocode specs (deep phase)
├── reviews/              ← Reviewer: verification reports
├── exploration/          ← Explorer: search results, dependency maps
├── learnings/            ← System Thinker: meta-cognitive recordings
├── ratings/              ← Orchestrator: session-end user ratings
└── project_notes/        ← Orchestrator: institutional memory (ADRs, bugs, issues)
```

## Do-Nots

- **Do NOT** use Node.js/npx — use conda + bun
- **Do NOT** rely on `src/index.ts` — dead code
- **Do NOT** hardcode secrets 
- **Do NOT** use "roo_agent" as user_id — stale, from Roo Code era
- **Do NOT** exceed 10GB VRAM / 32GB RAM
- **Do NOT** add auth/multi-tenancy — single user only

## Source Files

- `src/main.py` — v0 MCP server. 5 tools (add/search/delete/sync/list), in-process Mem0, forward-compatible metadata, path validation. Port 8000. `infer=True` hardcoded (pending ADR-020 change).
- `src/test_main.py` — 50 tests: config loading, filter construction, all 5 tools, path validation, no hardcoded values. Mock-based, no live infra.
- `tests/integration/` — Not yet created. Will contain live ingestion tests per ADR-021.
- `src/pyproject.toml` — Python dependencies (fastmcp, mem0ai, httpx, uvicorn, pyyaml, pytest, pydantic, etc.)
- `src/config.json` — MCP server config. Transport: `streamable-http`. URL: `http://0.0.0.0:PORT/mcp`.
- `Dockerfile` — Builds from `framework-opencode:latest`, conda env `dev1`, uv pip install.
- `.env` — **Deleted.** No .env file exists. Env vars set via shell/Docker or defaults in src/main.py.
- `.opencode/memory/` — Legacy memory system (DECISIONS.md, CONTEXT.md, STACK.md, handoff.md). Git-tracked. To be deleted when mem0 takes over.

## Future Architecture (Proxy Pattern) — IN PROGRESS

- Root `main.py` → proxy server that mounts internal memory service at `http://mcp-memory-service:8000/mcp`
- `src/main.py` → internal memory service (current v0 server)
- **Proxy endpoint**: `http://mcp-server:PORT/mcp` — external clients connect here
- Memory service attached as backend: `mcp.mount(create_proxy("http:mcp-memory-service:8000/mcp"), namespace="remote_api")`
- This allows the memory MCP server to be one of many services behind a single proxy endpoint
- Current focus: proving the ingestion pipe first, then wiring up proxy

---

## Tips

- Keep entries current — update when things change
- Include URLs for easy navigation
- Group related information together
- Mark deprecated items clearly with dates