# Project Context

**Overwritten each session. This is the current state snapshot.**

---

## Current State: Planning Phase

**Phase**: Requirements & architecture planning. No code written this session. The server will eventually be a proxy MCP server built on FastMCP, but the current priority is getting an accurate memory working first.

### What exists

**`src/main.py`** — In-process mem0 implementation with Qdrant + Ollama. Has the right shape but needs cleanup (duplicate imports, hardcoded user_id, manifest file approach). Currently runs on port 8001. **Not yet functional.**

**`main.py`** (root) — Minimal FastMCP proxy scaffold. Mounts a proxy to `mcp-memory-service:8000/mcp` under namespace `remote_api`. The proxy target will fail — no container provides it. Runs on port 8001.

**`src/pyproject.toml`** — Python 3.14+, dependencies: fastmcp (3.2.4+), fastapi (0.136+), uvicorn, httpx, python-dotenv, mem0ai.

**`docker-compose.yml`** — Single service `mcp-server` on `internal-net`. Traefik labels route to port 6274 (vestigial). Container exposes 8001. User connects directly on port 8000.

**`.agents/skills/mem0/`** — mem0ai/mem0@mem0 skill installed (official, 604 installs). SDK references available. No code integration yet.

**`.memory/`** — Temporary project memory system (DECISIONS.md, CONTEXT.md, STACK.md, handoff.md). Git-tracked. Will be deleted when mem0 takes over.

### What doesn't exist yet

- No working MCP server (neither proxy nor memory)
- No mem0 integration (skill installed, code not wired)
- No `.env` or `.env.example` file
- No tests
- No multi-container architecture (Qdrant + Ollama are external infrastructure, user-managed)
- No defined MCP tool interface (planning in progress)
- No defined data model for memories

### Key Architectural Decisions (So Far)

- **Memory runs in-process** — mem0ai imported as a Python library inside this container. Simple to move to a separate container later if needed.
- **Serving port: 8000** — Settled. Both main.py files currently run on 8001, need alignment to 8000.
- **Single user** — The user connects directly. No auth, no multi-tenancy.
- **OpenCode, not Roo Code** — The agent context has changed. "roo_agent" user_id in src/main.py is stale and must be updated.

### External Infrastructure (User-Managed)

- **Qdrant** — Vector store. Must be accessible at the host/port configured via `QDRANT_HOST`/`QDRANT_PORT` env vars. Not in this repo's compose.
- **Ollama** — LLM + embeddings. Must be accessible at `OLLAMA_URL`. Not in this repo's compose. Embedding model: bge-m3 (or configurable via `EMBEDDING_MODEL`).

---

## Active Blockers

1. **No working server** — Both main.py files have issues (broken proxy reference, port mismatch, stale user_id)
2. **No mem0 integration** — Skill installed, no code wired
3. **No env var handling** — No `.env` file, no `.env.example`
4. **Port misalignment** — Serving should be 8000, both main.py files run on 8001

---

## Next Steps (Priority Order)

1. **Planning phase** — Define MCP tool interface, data model, configuration surface, failure modes, extensibility points. Skills being installed to help: `mem0ai/mem0@mem0`, `wshobson/agents@architecture-patterns`, `othmanadi/planning-with-files@planning-with-files`
2. **Fix server entry point** — Settle on one main.py at root, port 8000, remove broken proxy reference
3. **Wire mem0** — Configure Memory.from_config() with env vars, expose MCP tools
4. **Add `.env.example`** — Document required env vars (QDRANT_HOST, QDRANT_PORT, OLLAMA_URL, EMBEDDING_MODEL)
5. **Update user_id** — Replace "roo_agent" with generic agent identifier

---

## Last Updated: 2026-04-23