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

## Agent Team

- **Coordinator** (primary): opencode-go/glm-5.1 — Orchestrates, tracks goals, user gates, delegates to experts
- **Expert** (all): opencode-go/kimi-k2.5 — Domain knowledge (FastMCP, Mem0, architecture, ADRs). Lazy-loads skills. Read-only advisor.
- **Explorer** (subagent): opencode-go/minimax-m2.7 — Read-only scout, file search, pattern discovery
- **Implementer** (subagent): opencode-go/kimi-k2.5 — Code writing, Python/FastMCP syntax. Receives approved specs only.
- **Reviewer** (subagent): opencode-go/kimi-k2.5 — Read-only code verification, fox/henhouse prevention

### Delegation Model: 3-Layer with User Gates

```
WHY  → Coordinator (goals, decisions, user sign-offs) (OUTDATED -> Product_owner succeeeds)
HOW  → Expert (domain knowledge, options, specifications)
WHAT → Implementer (code, syntax, implementation)
```

- Every stage transition requires user approval (no autonomous pipeline)
- Coordinator asks expert for options → user approves → coordinator delegates to implementer → user approves → reviewer verifies → user signs off

### Agent Config Files

- `opencode.jsonc` — 5 agents defined (coordinator, expert, implementer, explorer, reviewer)
- `prompts/coordinator.md` — Updated: 3-layer delegation, user gates, @expert delegation (OUTDATED)
- `prompts/expert.md` — Domain principles + skill index + anti-staleness rules + read-only
- `prompts/implementer.md` — Syntax-focused, spec-driven, project conventions
- `prompts/reviewer.md` — Priority-based review (Blocker/Major/Minor/Suggestion), spec compliance
- `prompts/explorer.md` — Unchanged from previous session
- Old `prompts/coder.md` — Deleted by user

### Session Persistence

- Expert sessions (Task tool) are ephemeral — do not persist across OpenCode restarts
- Coordinator carries institutional memory via `docs/project_notes/`
- V2: Expert could use MCP server memory to persist architectural decisions across sessions

### Delegation Mechanisms

- **Tier 1**: Task tool — fast, in-process, for explorer + simple lookups
- **Tier 2**: CLI `opencode run --agent <name>` — full agent context, blocking
- **Tier 3**: Server API / Plugin — async, lifecycle control, parallel execution

### Skill Injection Pattern (ADR-017, supersedes ADR-016)

- **Domain expertise** baked into expert agent prompt (FastMCP patterns, Mem0 SDK, hexagonal architecture, Python/MCP best practices)
- **Project context** passed by coordinator per-task (relevant ADRs, key facts, current goal scope, constraints)
- Expert only knows the current goal — not the entire project overview
- Coordinator owns project overview (how goals fit together, priority ordering)
- v2 stretch goal: Expert directly injects context into implementer

### Planning Files

- `task_plan.md` / `findings.md` / `progress.md` — MCP server architecture (complete, 5/5 phases)
- `task_plan_agents.md` / `findings_agents.md` / `progress_agents.md` — Agent team architecture (Phase 1/6 complete)

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