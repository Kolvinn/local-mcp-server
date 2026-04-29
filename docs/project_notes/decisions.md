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

### ADR-015: Three-Agent Team with Tiered Delegation (2026-04-23) — SUPERSEDED by ADR-018

**Context:**
- Current `coder` agent is too generic — no specialization, no verification loop, no domain knowledge injection
- Need agent team that can tackle 7 implementation priorities with proper separation of concerns

**Decision:**
- 3 subagents: explorer (read-only scout), implementer (writes code), reviewer (verifies code). Coordinator injects skill knowledge into delegation prompts. Tiered delegation: Task tool (fast) → CLI (full context) → Server API/plugin (async, lifecycle).

**Superseded by:**
- ADR-018 expanded to 5 agents with dedicated domain expert (explorer, expert, implementer, reviewer + coordinator)
- ADR-017 replaced coordinator-side skill injection with expert agent pattern + user gates

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
- ❌ SUPERSEDED: No domain expert role, coordinator was knowledge middleman (ADR-017 fixes this)

---

### ADR-016: Coordinator-Side Skill Injection (2026-04-23) — SUPERSEDED by ADR-017

**Context:**
- Skills (`.agents/skills/`) contain domain knowledge. Subagents cannot load skills themselves.
- Need a mechanism to make skill knowledge available to subagents.

**Decision:**
- Coordinator loads skill content, then includes relevant portions in task delegation prompts. The skill is a coordinator tool, not a subagent tool.

**Superseded by:**
- ADR-017: Domain expert agent owns skill knowledge (baked into prompt). Coordinator asks expert for condensed options instead of loading skills itself.

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
- ❌ SUPERSEDED: Coordinator is middleman — ADR-017 bakes skills into expert agent prompt instead

---

### ADR-017: 3-Layer Delegation with User Gates (2026-04-24)

**Context:**
- ADR-016 had coordinator injecting skill knowledge into subagent prompts — middleman pattern, wasteful and lossy
- Need clear separation of concerns: why (coordinator), how (expert), what (implementer)
- User must approve at every stage transition — no autonomous pipeline

**Decision:**
- 3-layer delegation: Coordinator (why) → Domain Expert (how) → Implementer (what), with user approval gates between each stage
- Domain expert is a permanent `all`-mode OpenCode agent
- **Expert prompt contains domain expertise only** (FastMCP patterns, Mem0 SDK reference, hexagonal architecture principles, Python/MCP best practices). NOT project-specific context.
- **Coordinator passes project context per-task** (relevant ADRs, relevant key facts, current goal scope, constraints). Expert only knows what goal is being worked on, not project overview.
- Coordinator owns project overview — goals, how they fit together, priority ordering. Expert owns domain knowledge.
- Expert output goes through coordinator → user approval → implementer delegation
- Reviewer remains separate (read-only verification, fox/henhouse prevention)
- Explorer remains read-only scout
- Stretch goal v2: Expert directly injects context into implementer (skip coordinator pass-through)

**Alternatives Considered:**
- ADR-016 coordinator-side injection → Superseded: middleman pattern, bloats coordinator context, lossy compression
- All context baked into expert prompt → Rejected: expert carries stale project context, prompt bloats with irrelevant ADRs/key facts
- Fully autonomous pipeline (no user gates) → Rejected: user must approve each stage to maintain intent alignment
- Expert also self-reviews → Rejected: fox/henhouse problem

**Consequences:**
- ✅ Coordinator context stays clean — orchestrates only, owns project overview
- ✅ Expert prompt stays lean — domain expertise only, no project-specific context
- ✅ Project context passed per-task — always current, never stale, scoped to the goal at hand
- ✅ User in the loop at every stage gate (expert options, implementation, verification)
- ✅ Implementer is lean — receives approved specs, writes code
- ✅ Clear separation: why (coordinator) / how (expert) / what (implementer)
- ❌ More round-trips per feature (but every round-trip has user intent alignment)
- ❌ Coordinator must craft concise project context for each expert delegation
- ❌ v1: Coordinator passes expert output to implementer (future: direct injection)

---

### ADR-018: 5-Agent Team with Domain Expert (2026-04-24)

**Context:**
- ADR-015 defined 3 agents (explorer, implementer, reviewer) — no domain knowledge specialist
- ADR-017 established 3-layer delegation (coordinator/expert/implementer) requiring a dedicated expert agent
- The "implementer" role needs to be split: expert owns domain knowledge, implementer owns code syntax

**Decision:**
- 5-agent team: Coordinator (primary), Expert (all), Explorer (subagent), Implementer (subagent), Reviewer (subagent)
- Expert is `all`-mode — delegated to by coordinator, but also user-switchable for direct questions
- **Expert prompt: domain expertise only** — FastMCP patterns, Mem0 SDK, hexagonal architecture, Python/MCP best practices. No project ADRs, key facts, or goal overview.
- **Coordinator passes project context per-task** — relevant ADRs, key facts, current goal scope, constraints. Expert only sees what's needed for the current task.
- **Coordinator owns project overview** — how goals fit together, priority ordering, what's been done. Expert only knows the current goal.
- Implementer receives approved specs only — lean prompt with Python/FastMCP syntax, no domain architecture
- Explorer and Reviewer unchanged from ADR-015 design
- Model: Expert=kimi-k2.5, Implementer=kimi-k2.5, Explorer=minimax-m2.7, Reviewer=kimi-k2.5

**Alternatives Considered:**
- 3-agent team (ADR-015 original) → Superseded: no domain knowledge specialist
- Expert also implements → Rejected: mixing how and what responsibilities
- 6+ agents (separate expert per domain) → Rejected: over-engineering for v1, domains are tightly coupled
- All context baked into expert → Rejected: stale project context, prompt bloat, expert doesn't need to know about goals it's not working on

**Consequences:**
- ✅ Clean role separation: why (coordinator) / how (expert) / what (implementer)
- ✅ Expert can be directly consulted by user (all-mode)
- ✅ Expert prompt stays lean and stable — domain knowledge doesn't change per task
- ✅ Project context is always fresh — passed per delegation, not baked in
- ✅ Coordinator retains project overview without being a domain middleman
- ✅ Implementer prompt stays lean (syntax only)
- ❌ 5 agents to configure vs 3
- ❌ More delegation steps per feature
- ❌ Coordinator must scope project context for each expert delegation

---

### ADR-019: v0 Pivot — Working Server Over Directory Structure (2026-04-24)

**Context:**
- 5 sessions of architecture planning completed, zero running code. Directory structure was next priority but serves HOW, not WHY.
- User is a contractor building a system that grows with them. Needs to start ingesting permanent memory now, not after more planning.
- Forward-compatible metadata schema ensures no re-ingest when expanding later.

**Decision:**
- Pivot from hexagonal directory structure to single-file v0 implementation. 5 tools (add_memory, search_memory, delete_memory, sync_metadata, list_projects) in one `src/main.py`. No ports/adapters. Just working code with forward-compatible data model.
- Every memory includes full metadata schema from day 1: tags, project_id, source_user, related_files, source_path, validated_at. Future expansions are additive — no re-ingest.
- Hexagonal refactor deferred to v1.0 (structural only, no functional changes).

**Alternatives Considered:**
- Continue with directory structure → Rejected: planning-as-procrastination, no working code for 6th session
- Full v1 (7 tools + hexagonal) → Rejected: too much for one session, delays ingestion further
- v0 without forward-compat fields → Rejected: guarantees re-ingest later

**Consequences:**
- ✅ Working MCP server — can start ingesting permanent memory immediately
- ✅ Forward-compatible — all future expansions are additive, no re-ingest
- ✅ Validated by 50 tests + code review (2 blockers, 1 major found and fixed)
- ✅ Hexagonal design preserved as refactor target (not lost)
- ❌ Single file — will need restructuring as features grow
- ❌ 2 of 7 v1 tools deferred (validate_memories, audit_stale → v0.1; compact_session → v0.2)
- ❌ docker-compose.yml and config.json still point to port 8001 (separate fix)

---

### ADR-020: add_memory `infer` Parameter — Optional, Default True (2026-04-25)

**Context:**
- `add_memory` was hardcoded with `infer=True`, meaning every call triggers local LLM (llama3.1:8b) fact extraction via Mem0
- Hardware constraint: RTX 3080 10GB VRAM must hold both nomic-embed-text (~274MB) + llama3.1:8b (~6-8GB)
- Primary callers are LLM agents (Claude, etc.) that already understand the content and could extract their own facts before sending
- Local LLM fact extraction is weaker than agent-side extraction but provides automatic deduplication via Mem0

**Decision:**
- Add `infer` as optional boolean parameter to `add_memory` (default `True` for backward compat)
- `infer=False` skips LLM fact extraction entirely — only embedding + storage
- `infer=True` (current behavior) runs local LLM fact extraction with dedup
- **Open question (pending user decision)**: Should default change to `False` in future since agents are primary callers?
- When `infer=False`: agent is responsible for extracting facts before calling add_memory. No dedup.
- When `infer=True`: server does extraction + dedup. Higher VRAM, higher latency, lower fact quality.

**Alternatives Considered:**
- Keep `infer=True` hardcoded → Rejected: removes control, wastes VRAM when agents are callers
- Change default to `False` immediately → Rejected: pending broader architectural decision about fact extraction responsibility
- Remove infer entirely, always do both → Rejected: unnecessary VRAM usage for agent-driven ingestion

**Consequences:**
- ✅ Immediate: can test base embedding path without LLM
- ✅ Production: agents can skip LLM extraction when they've already extracted facts
- ✅ Flexibility: bulk ingestion scripts can still use `infer=True` for automated extraction
- ❌ `infer=False` loses Mem0's automatic deduplication — agent must handle redundancy
- ❌ Two code paths to test and maintain
- ❌ Default `True` means first-time users hit the heavy path

---

### ADR-021: Live Ingestion Test Architecture (2026-04-25)

**Context:**
- 50 mock tests exist (test_main.py) but zero tests against live infrastructure
- Need to verify end-to-end: add_memory → Qdrant storage → Ollama embedding → search → delete
- Test must go through MCP protocol (streamable-http), not direct function calls
- Future architecture: root main.py becomes proxy server, internal memory server mounts into it
- Cleanup strategy: delete Qdrant collections, not individual memories. No permanent data until pipe is proven.
- All services run on `internal-net` Docker network. Tests execute inside Docker.
- Ollama currently has: nomic-embed-text (embeddings), llama3.1:8b (LLM)

**Decision:**
- Phase 1 test plan: 11 tests, 3 memories (2 global, 1 project-scoped)
- Test both `infer=False` (embedding-only) and `infer=True` (LLM extraction) paths
- Cleanup via Qdrant collection deletion, not individual delete_memory calls
- Test runner runs inside Docker on `internal-net`
- Test `AGENT_ID=test_ingest` for isolation from real data
- Tests via MCP protocol (httpx POST to /mcp), not direct imports

**Alternatives Considered:**
- Direct function call tests → Rejected: server is consumed via MCP protocol, must test end-to-end
- 60-memory volume test as phase 1 → Rejected: too much for initial validation, prove the pipe first then scale
- Cleanup via delete_memory per item → Rejected: Qdrant collection deletion is cleaner and more reliable for test isolation
- Test from host (outside Docker) → Rejected: production architecture is inside Docker on internal-net

**Consequences:**
- ✅ Proves end-to-end pipe before any permanent data ingestion
- ✅ Two infer paths tested independently (embedding-only vs LLM extraction)
- ✅ Clean test isolation via AGENT_ID and collection deletion
- ❌ Requires Docker environment to be running for tests
- ❌ Requires Ollama models pulled before tests will pass

---

### ADR-022: Delegation Protocol Fix — Expert Spec Flow, User Gates, Wide Before Deep (2026-04-27)

**Context:**
- Coordinator (product_owner) was violating protocol by: (1) giving implementer specific code instructions, (2) skipping expert for architectural decisions, (3) not maintaining session continuity
- Prompt misalignment: expert wrote full specs before user approval; no clear rule about when to go wide vs deep
- opencode.jsonc is source of truth for permissions/models, but prompts had duplicate YAML frontmatter

**Decision:**
- Expert goes **wide before deep**: condensed options first, full spec only AFTER user approval
- Expert writes tech spec to `docs/specs/{feature_name}.md`, sends coordinator only a **summary** (not full spec)
- Coordinator NEVER reads the spec file — summary is sufficient for tracking
- Coordinator relays spec file location + summary to implementer
- 3 explicit approval gates: (1) approve option → (2) approve spec → (3) approve implementation
- Session continuity: always pass `task_id` to continue expert sessions instead of cold-starting
- I NEVER write code — state goals/constraints/outcomes only
- YAML frontmatter removed from prompts/expert.md and prompts/implementer.md (opencode.jsonc is source of truth)

**Prompts Updated:**
- `prompts/product_owner.md`: Added approval gates section, session continuity, iterative clarification (wide before deep), "I never write code" rule, direct delegation threshold
- `prompts/expert.md`: Wide before deep protocol, spec file output, summary-only to coordinator
- `prompts/implementer.md`: Receives spec file location + summary (not context dumps), reads spec file directly

**Alternatives Considered:**
- Keep code instruction to implementer → Rejected: I have no domain expertise, can't architect correctly
- Expert sends full spec to coordinator → Rejected: bloats coordinator context, defeats purpose of spec file
- Cold-start expert each time → Rejected: wasteful, repeated initialization
- Skip user gates → Rejected: user must approve at each stage

**Consequences:**
- ✅ Cleaner separation: why (coordinator) / how (expert) / what (implementer)
- ✅ User in loop at every decision point
- ✅ Expert sessions efficient via task_id continuity
- ✅ Specs stored in docs/specs/ for future reference
- ❌ More round-trips per feature
- ❌ Coordinator must trust expert spec without reading it

---

### ADR-023: Clean Separation of Concerns — Single Orchestrator + Spawnable System Thinker (2026-04-29)

**Context:**
- Coordinator and Product Owner both existed as `primary`-mode agents with ~95% overlapping scope: user contact, goal ownership, delegation, approval gates. Two agents fighting for the same responsibilities.
- Product Owner was designed to replace Coordinator but the overlap created ambiguity about who the user talks to and who owns what.
- Expert was a fixed agent with domain patterns (FastMCP, Mem0, hexagonal) baked into its prompt — not portable across projects.
- Prose specs from Expert left an interpretation gray zone for Implementer and Reviewer.

**Decision:**
- **Single Orchestrator** (primary) as sole user contact. Owns: goals, workflow state, delegation, approval gates. Anti-scope: never designs, never codes, never explores, never reviews.
- **System Thinker** (all-mode, spawnable template) replaces Expert. Base prompt is project-agnostic methodology (trade-off analysis, pseudocode production, consequence reasoning, learning recording). Domain expertise injected via skills loaded per-delegation.
- **Implementer** rewritten as project-agnostic translator: reads `docs/context/`, translates pseudocode → production code. No design decisions. No project specifics baked in.
- **Reviewer** updated to verify code against pseudocode spec (structural diff, not prose intent inference). Writes full review to file, returns summary.
- **Explorer** updated with structural analysis tools (dependency graphs, call chains, import maps, impact radius). File-only output protocol: writes to `docs/exploration/`, returns only `complete` or `error`.
- **Agent Creator removed** — shelved for future revisit.
- **Product Owner, Coordinator, Expert, agentic_architect removed** from opencode.jsonc.
- **Transparency protocol**: every agent writes full output to file, passes condensed summary to consumer.
- **Three-tier context model**: Tier 1 (methodology, baked in prompt), Tier 2 (domain, `docs/context/`), Tier 3 (task, delegation prompt).
- **Pseudocode handoff**: System Thinker produces pseudocode specs with method signatures, error conditions, side effects, transactional relationships. Implementer translates (doesn't interpret). Reviewer verifies structural compliance.
- **4 approval gates**: Approach (G1) → Spec (G2) → Code (G3) → Review (G4). Gates are lightweight confirmations; trivial changes can skip intermediate gates with user consent.
- **File access protocol**: Orchestrator uses `head -c 5000` byte sampling before reading any non-context file directly. Source code always delegated to Explorer. User instruction overrides threshold.
- **Evolution mechanism**: Orchestrator collects session ratings → `docs/ratings/`. Accumulated data feeds improvement runs that refine agent prompts.
- **Learning recording**: System Thinker writes learnings to `docs/learnings/{domain}/{session}.md` for cross-instance continuity.

**Alternatives Considered:**
- Keep dual entry agents (Coordinator + PO) → Rejected: overlapping scope causes ambiguity and diluted responsibility
- Fixed Expert with baked domain knowledge → Rejected: not portable, stale risk, can't spawn multiple instances
- Single-use agents (one per task) → Rejected: wasteful, no cross-instance learning

**Consequences:**
- ✅ Zero overlapping responsibilities across all agents
- ✅ Project-agnostic — same agent team works on any project by swapping `docs/context/`
- ✅ Pseudocode handoff eliminates interpretation gray zone
- ✅ File + summary protocol: transparency without context bloat
- ✅ Dynamic spawning: multiple Thinker instances for complex parallel analysis
- ✅ Evolution-ready: ratings + learnings feed improvement cycle
- ❌ Sequential pipeline is inherently slower than parallel
- ❌ Pseudocode depth calibration requires iteration
- ❌ System Thinker instantiation requires Orchestrator to specify skill loads correctly
- ❌ Stale files removed (coordinator.md, product_owner.md, expert.md, agentic_architect.md, agent-creator.md, agent_team.md)

---

### V2 Backlog

- **Expert Persistent Memory**: Once MCP server is built, expert agents could use add_memory/search_memory to persist architectural decisions across sessions. Currently expert sessions are ephemeral (no persistence across OpenCode restarts). Coordinator carries institutional memory via docs/project_notes/.
- **Evolution Pipeline Automation**: Automatic analysis of accumulated ratings to propose prompt improvements.
- **Agent Creator Revisit**: Rebuild with the System Thinker template model.