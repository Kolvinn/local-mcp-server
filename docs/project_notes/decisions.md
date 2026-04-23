# Architectural Decisions

Architecture Decision Records (ADRs). Immutable — append only. Never delete or edit past entries.

---

### ADR-001: MCP Proxy Server Architecture (2026-04-23)

**Context:**
- Need a central MCP server that any LLM can connect to, proxying requests to multiple downstream Docker containers

**Decision:**
- Use FastMCP (Python) as the composite orchestrator with `create_proxy()` to mount downstream services

**Alternatives Considered:**
- Node.js MCP SDK → Rejected: Python ecosystem gives us mem0ai, httpx, FastAPI/uvicorn
- Raw SSE server → Rejected: no namespace support, harder composition

**Consequences:**
- ✅ Python-first stack. Rich ecosystem.
- ✅ Single entry point for all LLM clients
- ✅ Native proxy-composition with namespace support
- ❌ Downstream services must expose MCP-compatible endpoints
- ❌ Routing through Traefik for internal container-to-container communication

---

### ADR-002: Docker Container Chain via Traefik (2026-04-23)

**Context:**
- Multiple Docker containers need to communicate on an internal network. Only the user connects from outside the container.

**Decision:**
- Use Traefik as the internal reverse proxy. Containers communicate on `internal-net`. The mcp-server container serves on port 8000 — the user is the only external consumer.

**Alternatives Considered:**
- Direct container-to-container networking → Rejected: no automatic service discovery, harder to manage
- Nginx reverse proxy → Rejected: Traefik integrates natively with Docker Compose labels

**Consequences:**
- ✅ Dynamic routing via Docker labels
- ✅ Native Docker Compose integration
- ✅ TLS handling built-in
- ❌ All containers must join `internal-net`
- ❌ Port 6274 label in docker-compose is vestigial inspector cruft

---

### ADR-003: Roll-Your-Own Project Memory via .memory/ (2026-04-23)

**Context:**
- Need persistent project memory across sessions until mem0 is integrated. Evaluated `opencontext`, `project-memory`, `conversation-memory`, `project-session-management` skills — all had security audit failures or were over-engineered for temporary use.

**Decision:**
- Create lightweight `.memory/` directory with structured markdown files (DECISIONS.md, CONTEXT.md, STACK.md, handoff.md). No external dependencies. Will be replaced by mem0 once integrated.

**Alternatives Considered:**
- opencontext skill → Rejected: security audit failure
- project-memory skill → Rejected: over-engineered for temporary use (note: now adopted in `docs/project_notes/` format)
- conversation-memory skill → Rejected: security audit failure

**Consequences:**
- ✅ Zero security risk, zero dependencies
- ✅ Git-trackable, trivially replaced
- ❌ Manual upkeep required
- ❌ Replaced by `docs/project_notes/` (project-memory skill format) — `.memory/` to be deleted

---

### ADR-004: Dual Runtime — Python Primary, Bun/TypeScript Placeholder (2026-04-23)

**Context:**
- Project has both Python (FastMCP/mem0ai) and TypeScript (placeholder `index.ts`) runtimes in `src/`

**Decision:**
- Python is the primary runtime. TypeScript is scaffolding/placeholder only. Bun is available for any future TS tooling.

**Alternatives Considered:**
- Pure TypeScript/Node → Rejected: FastMCP, mem0ai, FastAPI are all Python
- Dual primary runtime → Rejected: unnecessary complexity for v1

**Consequences:**
- ✅ Clear single-language focus
- ✅ Bun available if needed later
- ❌ `src/index.ts` is dead code — don't waste time on it

---

### ADR-005: Container Base Image — framework-base (2026-04-23)

**Context:**
- Dockerfile uses `FROM framework-base:latest` which is a custom pre-built image

**Decision:**
- Accept the custom base image. It already has conda. Install bun and uv on top.

**Alternatives Considered:**
- Build from ubuntu/python base → Rejected: adds 50+ lines of Dockerfile boilerplate
- Use official python image → Rejected: doesn't include conda setup

**Consequences:**
- ✅ Minimal Dockerfile, consistent conda environment
- ❌ Must ensure `framework-base:latest` is available in the Docker build context
- ❌ Pinning the tag may be needed for reproducibility

---

### ADR-006: Single-User Access Model (2026-04-23)

**Context:**
- This MCP server container serves as the brains that any LLM connects to, but the only external consumer is the user themselves.

**Decision:**
- No multi-tenancy, auth layers, or public-facing UI. The user connects directly. Access control is at the infrastructure level (Docker network, local access only).

**Alternatives Considered:**
- JWT/API key auth → Rejected: single user, no need
- OAuth flow → Rejected: massively over-engineered for single user

**Consequences:**
- ✅ Significantly simplified architecture
- ✅ No auth middleware, no rate limiting, no session management
- ❌ If multi-user access is needed later, it's a separate scope

---

### ADR-007: In-Process Mem0 Architecture (2026-04-23)

**Context:**
- Need to decide where mem0 runs — inside this container as a Python library import, or as a separate downstream MCP service container.

**Decision:**
- mem0ai runs as an in-process Python library import inside this container. Qdrant and Ollama are external infrastructure managed by the user.

**Alternatives Considered:**
- Separate mem0 container → Rejected: unnecessary for v1, moving to separate container later is trivial if needed
- mem0 as external service → Rejected: adds network latency and deployment complexity

**Consequences:**
- ✅ Simple for v1 — minimal architecture
- ✅ Moving mem0 to its own container later is trivial
- ❌ This container's sole responsibility is exposing MCP tools backed by mem0
- ❌ Qdrant and Ollama must be accessible via env vars (QDRANT_HOST, QDRANT_PORT, OLLAMA_URL, EMBEDDING_MODEL)

---

### ADR-008: Planning-First Approach (2026-04-23)

**Context:**
- Previous session went too fast into code without adequate planning. The planning phase was skipped, leading to fragmented code and unclear interfaces.

**Decision:**
- Spend this session on planning before any code is written. Define: (1) MCP tool interface, (2) data model for memories, (3) configuration surface, (4) failure modes and edge cases, (5) extensibility points.

**Alternatives Considered:**
- Code-first with documentation → Rejected: led to fragmented code last time
- Test-first → Rejected: no interface defined yet, nothing to test against

**Consequences:**
- ✅ Clear interface definitions before implementation
- ✅ Better extensibility design
- ❌ Slower start — no visible code progress during planning
- ❌ Skills installed to support: mem0ai/mem0@mem0, architecture-patterns, planning-with-files

---

### ADR-009: Agent Context — OpenCode, Not Roo Code (2026-04-23)

**Context:**
- The agent context has shifted from Roo Code to OpenCode. The user_id "roo_agent" in src/main.py is stale and must be updated.

**Decision:**
- Replace all references to "roo_agent" with a generic agent identifier appropriate for OpenCode. Make it configurable rather than hardcoding any agent brand.

**Alternatives Considered:**
- Keep "roo_agent" → Rejected: stale, misleading
- Hardcode "opencode_agent" → Rejected: still agent-specific, same problem

**Consequences:**
- ✅ Agent-agnostic identifier
- ✅ Configurable for any future agent context
- ❌ Any user_id, project_id, or agent-specific hardcoding must be reviewed and updated

---

### ADR-010: Dual-Layer Memory Architecture (2026-04-23)

**Context:**
- Need both semantic vector memory and hierarchical local metadata for context injection

**Decision:**
- Layer 1: Mem0 + Qdrant (semantic). Layer 2: `.memory-context.yaml` files auto-discovered per directory. Local files are search lenses (tags/scope), not record pointers. Coupling via shared vocabulary (tags, project_id), not explicit memory_ids.

**Alternatives Considered:**
- Mem0 only → Rejected: no hierarchical context, no folder-local scoping
- Local files only → Rejected: no semantic search
- Explicit cross-references (memory_ids in YAML) → Rejected: brittle, high maintenance overhead

**Consequences:**
- ✅ Each layer does what it's best at
- ✅ `.memory-context.yaml` cascade: folder-local > project-level, tags accumulate
- ❌ Two systems to maintain
- ❌ Staleness across layers must be validated

---

### ADR-011: Git-First Drift Detection, No Stored Hashes (2026-04-23)

**Context:**
- Need to detect when memories reference files that have changed

**Decision:**
- Store `related_files: [{path, entered}]` per memory. At audit time, query `git log --since=<entered> -- <path>`. No hashes, no git commits stored — git already tracks this.

**Alternatives Considered:**
- SHA-256 content hash per file → Rejected: duplicates git's job, no diff context
- Store git commit SHA per file → Rejected: duplicates git, blind to uncommitted changes
- Hybrid (git + hash fallback) → Rejected: overkill for agentic memory, not file indexing

**Consequences:**
- ✅ Minimal storage overhead
- ✅ `git diff` gives rich change context at audit time
- ✅ No duplication of git's job
- ❌ Git must be available for full drift detection (fallback: validated_at window only)
- ❌ No drift detection for non-repo files

---

### ADR-012: Three-Dimension Scoping Model (2026-04-23)

**Context:**
- Memories need to be scoped by who created them, what project, and who they're about (future: business partners/clients)

**Decision:**
- `user_id` = who created it (from AGENT_ID env var). `project_id` = what project (from `.memory-context.yaml`). `source_user` = who it's about (optional, passed at add_memory time).

**Alternatives Considered:**
- user_id only → Rejected: no project isolation, no human reference tracking
- user_id + project_id only → Rejected: can't track "Jane from Acme said X" structurally
- Tags only for human references → Rejected: fuzzy, can't do exact-match queries on people

**Consequences:**
- ✅ Clean query: by creator, by project, by subject, or any combination
- ✅ source_user future-proofs for business partner/client expansion
- ❌ More fields per memory
- ❌ v2 will need richer contact model for source_user

---

### ADR-013: V1 Tool Surface — 7 Tools (2026-04-23)

**Context:**
- Need to define which MCP tools ship in v1 vs v2

**Decision:**
- V1: add_memory, search_memory, delete_memory, validate_memories, compact_session, audit_stale, sync_metadata. V2 deferred: cleanup_stale, check_drift, reingest pipeline, subagent workers.

**Alternatives Considered:**
- 10-tool surface with cleanup/drift → Rejected: insufficient data volume to warrant, LLM cost not justified
- Minimal 4-tool surface → Rejected: no staleness handling, no metadata management

**Consequences:**
- ✅ Focused v1 — no over-engineering
- ✅ search_memory includes on-retrieval staleness/git flags (no separate tool needed)
- ❌ Stale memories must be manually deleted or validated (no auto-cleanup)
- ❌ No drift detection beyond staleness window + git log

---

### ADR-014: Staleness via On-Retrieval Check (2026-04-23)

**Context:**
- Memories can become stale. Need a detection mechanism without background jobs.

**Decision:**
- On every `search_memory` call, check each result's `validated_at` against STALENESS_WINDOW_DAYS and run `git log --since` on related_files. Flagged results surfaced to user. `validate_memories` resets window. `audit_stale` for on-demand full scan.

**Alternatives Considered:**
- Background scheduled job → Rejected: complexity, resource usage
- Manual-only checking → Rejected: stale data silently persists

**Consequences:**
- ✅ Zero background infrastructure
- ✅ Stale data caught at the moment it matters most (when being used)
- ❌ Stale memories not flagged until someone searches for them
- ❌ Slight overhead on every search call

---

### ADR-015: Three-Agent Team with Tiered Delegation (2026-04-23)

**Context:**
- Current `coder` agent is too generic — no specialization, no verification loop, no domain knowledge injection
- Need agent team that can tackle 7 implementation priorities with proper separation of concerns

**Decision:**
- 3 subagents: explorer (read-only scout), implementer (writes code), reviewer (verifies code). Coordinator injects skill knowledge into delegation prompts. Tiered delegation: Task tool (fast) → CLI (full context) → Server API/plugin (async, lifecycle).

**Alternatives Considered:**
- Keep generic coder + skills only → Rejected: no verification loop, fox/henhouse problem
- 4+ agents (add architect) → Rejected: architecture planning is done, need implementation not design
- Pure Server API delegation → Rejected: adds latency, Task tool is sufficient for most tasks
- Pure background-agents plugin → Rejected: read-only limitation excludes implementer

**Consequences:**
- ✅ Clean write/verify separation
- ✅ Skill knowledge gets injected where needed
- ✅ Tiered delegation matches task complexity
- ❌ More coordination overhead (manual context injection)
- ❌ background-agents is read-only — implementer needs Task tool or custom plugin
- ❌ Three delegation patterns to learn

---

### ADR-016: Coordinator-Side Skill Injection (2026-04-23)

**Context:**
- Skills (`.agents/skills/`) contain domain knowledge. Subagents cannot load skills themselves.
- Need a mechanism to make skill knowledge available to subagents.

**Decision:**
- Coordinator loads skill content, then includes relevant portions in task delegation prompts. The skill is a coordinator tool, not a subagent tool.

**Alternatives Considered:**
- opencode-skillful plugin for lazy loading → Rejected: not yet evaluated, adds dependency
- Agent markdown files with embedded skill content → Rejected: duplicates knowledge, stale drift risk
- Skills as agent prompt includes → Rejected: would bloat all agent prompts with irrelevant context

**Consequences:**
- ✅ Subagents get relevant knowledge without needing skill access
- ✅ Coordinator controls what knowledge each delegation gets
- ✅ No duplication — single source of truth in skill files
- ❌ Coordinator context window bears the cost of loading skills
- ❌ Manual — coordinator must remember to inject relevant skill content