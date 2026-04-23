# Decision Log

Architecture Decision Records. Immutable — append only. Never delete or edit past entries.

---

## ADR-001: MCP Proxy Server Architecture
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Need a central MCP server that any LLM can connect to, proxying requests to multiple downstream Docker containers
- **Decision**: Use FastMCP (Python) as the composite orchestrator with `create_proxy()` to mount downstream services
- **Rationale**: FastMCP provides native proxy-composition with namespace support. Python ecosystem gives us mem0ai, httpx, FastAPI/uvicorn. Single entry point for all LLM clients.
- **Consequences**: Python-first stack. Downstream services must expose MCP-compatible endpoints. Routing through Traefik for internal container-to-container communication.

---

## ADR-002: Docker Container Chain via Traefik
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Multiple Docker containers need to communicate on an internal network. Only the user connects from outside the container.
- **Decision**: Use Traefik as the internal reverse proxy. Containers communicate on `internal-net`. The mcp-server container serves on port 8000 — the user is the only external consumer.
- **Rationale**: Traefik integrates natively with Docker Compose, supports dynamic routing via labels, handles TLS. The user connects directly to the container — no public-facing exposure needed.
- **Consequences**: All containers must join `internal-net`. Service discovery via Traefik labels. The port 6274 label in docker-compose was for the MCP Inspector UI (no longer used) connecting to the host machine — it is vestigial and can be ignored.

---

## ADR-003: Roll-Your-Own Project Memory (.memory/)
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Need persistent project memory across sessions until mem0 is integrated. Evaluated `opencontext`, `project-memory`, `conversation-memory`, `project-session-management` skills — all had security audit failures or were over-engineered for temporary use.
- **Decision**: Create lightweight `.memory/` directory with structured markdown files (DECISIONS.md, CONTEXT.md, STACK.md, handoff.md). No external dependencies. Will be replaced by mem0 once integrated. Tracked in git until mem0 takes over, then deleted.
- **Rationale**: Zero security risk, zero dependencies, git-trackable, trivially replaced. The discipline matters more than the tooling.
- **Consequences**: Manual upkeep required. Must update CONTEXT.md each session, DECISIONS.md for any significant choice. Delete `.memory/` and remove from git when mem0 takes over.

---

## ADR-004: Dual Runtime (Python + Bun/TypeScript)
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Project has both Python (FastMCP/mem0ai) and TypeScript (placeholder `index.ts`) runtimes in `src/`
- **Decision**: Python is the primary runtime. TypeScript is scaffolding/placeholder only. Bun is used as the JS runtime for any future TS tooling.
- **Rationale**: FastMCP, mem0ai, FastAPI, uvicorn are all Python. The tsconfig.json and `index.ts` are unused placeholders. Don't fight the ecosystem.
- **Consequences**: `src/index.ts` is dead code. Bun is available for any future JS utilities but not for core server logic.

---

## ADR-005: Container Base Image (framework-base)
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Dockerfile uses `FROM framework-base:latest` which is a custom pre-built image
- **Decision**: Accept the custom base image. It already has conda. We install bun and uv on top.
- **Rationale**: Standardizing on a custom base gives us conda + consistent Python. The alternative (building from ubuntu/python base) adds 50+ lines of Dockerfile boilerplate we don't need.
- **Consequences**: Must ensure `framework-base:latest` is available in the Docker build context. Pinning the tag may be needed for reproducibility.

---

## ADR-006: Single-User Access Model
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: This MCP server container serves as the brains that any LLM connects to, but the only external consumer is the user themselves.
- **Decision**: No need for multi-tenancy, auth layers, or public-facing UI. The user connects directly. Access control is handled at the infrastructure level (Docker network, local access only).
- **Consequences**: No auth middleware needed. No rate limiting. No multi-user session management. This simplifies architecture significantly. If multi-user access is needed later, it's a separate scope.

---

## ADR-007: In-Process Mem0 Architecture
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Need to decide where mem0 runs — inside this container as a Python library import, or as a separate downstream MCP service container.
- **Decision**: mem0ai runs as an in-process Python library import inside this container. Qdrant and Ollama are external infrastructure managed by the user.
- **Rationale**: Simple for v1. Keeps the architecture minimal. The "proxy MCP server" is a future state — this container will eventually proxy to multiple downstream MCP services, but that's a later phase. Currently, this container IS the memory service. Moving mem0 to its own container later is trivial if needed.
- **Consequences**: This container's sole responsibility in this phase is exposing MCP tools backed by mem0. Qdrant and Ollama must be accessible via env vars (QDRANT_HOST, QDRANT_PORT, OLLAMA_URL, EMBEDDING_MODEL). No docker-compose changes needed for mem0 itself.

---

## ADR-008: Planning-First Approach
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: Previous session went too fast into code without adequate planning. The planning phase was skipped, leading to fragmented code and unclear interfaces.
- **Decision**: Spend this session on planning before any code is written. Define: (1) MCP tool interface, (2) data model for memories, (3) configuration surface, (4) failure modes and edge cases, (5) extensibility points.
- **Rationale**: A robust, adaptable, extensible memory system requires upfront design. We need to define the interface the MCP tools expose, what a "memory" looks like under the hood, and how the system behaves when dependencies are unavailable. Skills installed to support: mem0ai/mem0@mem0, wshobson/agents@architecture-patterns, othmanadi/planning-with-files@planning-with-files.
- **Consequences**: Code implementation follows planning. No delegation to coder until planning is complete and aligned with user.

---

## ADR-009: Agent Context: OpenCode (Not Roo Code)
- **Date**: 2026-04-23
- **Status**: Accepted
- **Context**: The agent context has shifted from Roo Code to OpenCode. The user_id "roo_agent" in src/main.py is stale and must be updated.
- **Decision**: Replace all references to "roo_agent" with a generic agent identifier appropriate for OpenCode. This affects src/main.py user_id fields.
- **Rationale**: The MCP server is agent-agnostic. It should not hardcode a specific agent brand. Using a generic identifier (or making it configurable) is the correct approach.
- **Consequences**: Any user_id, project_id, or agent-specific hardcoding must be reviewed and updated before the server goes live.

---

<!-- Template for future handoffs:
## Handoff 002 — YYYY-MM-DD

**Who**: [agent/model]
**What was done**: [bullet list]
**What to do next**: [ordered list]
**Known gotchas**: [bullet list]
-->