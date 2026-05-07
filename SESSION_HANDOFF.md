# SESSION HANDOFF — Agentic Container Overhaul (Session 001)

**Date:** 2026-05-07
**Status:** Architecture validated. Phase 1 design ready to begin.
**Handoff to:** Next agent (orchestrator continuation) or human review.

---

## 1. Objective

Overhaul the local Docker setup from a single OpenCode MCP server into a **LangGraph-based multi-container agent system** powered by **Flox environments**.

- Each agent type = a modifiable template that adapts to injected context (e.g., Python implementer vs Java implementer)
- LangGraph for per-agent state management and the orchestrator's decision flow
- Flox per container for hermetic, reproducible environments
- MVP agent roster: **Implementer** + **Explorer** (Expert, Architect, Researcher, Reviewer are backlog)
- Agents **never communicate directly** — they write files or return summaries to orchestrator
- Agents **never access the host** — filesystem isolation via Docker volumes only
- User controls infrastructure, switches between projects, handles git

---

## 2. Current System State (What Exists)

### Working
- **FastMCP server**: 5 memory tools (add/search/delete/sync/list) on port 8000
- **Agent team v2 designed**: 5 agents (Orchestrator, System Thinker, Implementer, Reviewer, Explorer) with pseudocode handoff, 4-gate approval pipeline
- **mcp-mem0-update**: Fully complete (goal tree migration, 96 unit tests passing)
- **RAG pipeline A1+A2**: Pydantic models, edge contract (40 triples, 10 node types), chunker, embedder, Qdrant client — 82 tests pass
- **Diagrams**: Full orchestrator flow modeled (ORIENT→Clarify→Assess→Gather→Synthesize→Gate), two-tier RAG, anti-pattern guard nodes

### Diagrams Modeled (docs/diagrams/)
- `orchestrator-overview-v1.mmd` / `v2.mmd` — 5-phase + ORIENT phase 0
- `orchestrator-sequence-v1.mmd` — temporal agent interactions
- `orchestrator-thinking-loop.mmd` / `v2.mmd` — drill-down thinking + Memory Manager companion
- `loopold.mmd` — earlier iteration with anti-pattern guards
- See `docs/exploration/diagrams-summary.md` for summary

### Known Issues (from docs/project_notes/)
- Qdrant collections stale (1536-dim), need recreation at 768-dim
- Mem0 v3 API: `user_id` must be inside `filters` dict
- PORT=8001 still in `.env` causing 3 test failures
- Integration tests: 3/8 pass, 5 fail
- RAG paused at A3 (Graph DB integration — zero code, spec written)
- `infer` parameter not yet implemented

---

## 3. Architecture Evolution (The Full Debate)

### Starting Point
User wanted agents in Docker with filesystem isolation, no host access. Initial assumption: MCP file share server as the gatekeeper.

### 5 Approaches Debated

| Option | Mechanism | Rejected Because |
|--------|-----------|------------------|
| **A: MCP Gateway** | MCP file share server mounts host, agents call it for every read/write | Perpetual MCP latency on every file op |
| **B: Host Orchestrator** | Orch runs as host process, agents as containers | Loses containerization for orchestrator |
| **C: Static Bind + MCP** | Agents get ro bind mounts, MCP for writes | Two-tier model, static at boot |
| **D: Bind Mount Copy** | Orch copies files into agent workspace dirs | Copies don't scale for large repos |
| **Docker volume-subpath** | Named volume + per-agent subpath slices | Container restart needed to grant new subpaths |
| **OverlayFS** | Kernel overlay, writes to per-agent layer | Needs CAP_SYS_ADMIN, full visibility |

### Breakthrough: Symlink Bridge (VALIDATED)

User tested in `test-docker/`:
- **Shared volume** (`test-vol`): contains project files
- **Agent volume** (`agent-vol`): isolated per-agent
- **Orchestrator mounts BOTH** and creates symlinks from shared → agent volume
- Agent edits follow symlink → changes land directly in shared volume
- Init container confirms changes propagate

**This means:**
```
project-vol (shared)      orch bridges both       agent-vol (isolated)
┌──────────────┐          ┌──────────────┐        ┌──────────────┐
│ src/         │──────────│ /project/src/ │──ln -s─│ /ws/src/     │
│ tests/       │          │ /agents/a1/   │        │ /ws/tests/   │
│ docs/        │          │   src/ ───────┼──ln -s─│              │
│ config/      │ (hidden) │   tests/ ─────┼──ln -s─│              │
└──────────────┘          └──────────────┘        └──────────────┘
```

**Properties:**
- **Zero copies** — symlink IS the same inode
- **Zero host access** — agents only mount their own Docker volume
- **Zero Docker socket** — no `docker cp` or API calls
- **Dynamic grants** — `ln -s` to grant, `rm` to revoke, no container restart
- **Writes hit shared volume directly** — follow the symlink
- **Isolation** — agent sees only what orch symlinked into its volume

### Filesystem MCP Decision
Filesystem MCP was originally planned to gate file access. The symlink bridge makes it **redundant** for bulk I/O. Moved to **backlog**. MCP's remaining role: orchestrator↔agent communication protocol (task dispatch, results), not file serving.

---

## 4. Validated Architecture

**Three volume types, two container classes:**

| Volume | Purpose | Who mounts it |
|--------|---------|--------------|
| `project-vol` (named, external) | Source of truth for current project files | Orch (rw), Init (rw for population) |
| `agent-{name}-vol` (per agent) | Agent's isolated workspace | Orch (rw, for symlink mgmt), Agent (rw, for work) |

| Container | Mounts | Role |
|-----------|--------|------|
| Orchestrator | `project-vol` + all `agent-*-vol`s | Symlink bridge, task routing, state management |
| Agent (impl/expl) | Only its own `agent-*-vol` | Works blindly in its workspace |

### Test Files (test-docker/)
- `test-docker/test1.yml` — compose with 3 containers + 2 volumes
- `test-docker/Dockerfile.basetest` — base image (uv/python, apt tools, non-root user)
- The user manually validated: init writes → orch symlinks → agent edits → init sees changes

---

## 5. Current Plan (task_plan.md)

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Planning & context gathering | ✅ Complete |
| 1 | Volume topology + container model design | 🔄 In progress |
| 2 | LangGraph state management per agent | Pending |
| 3 | Orchestrator agent design (LangGraph stateflow) | Pending |
| 4 | RAG integration (complete paused A3-A6) | Pending |
| 5 | Implementation: Container + State | Pending |
| 6 | Implementation: Orchestrator + RAG | Pending |
| 7 | Polish, tests, docs | Pending |

---

## 6. Where Everything Lives

| Resource | Path | Contents |
|----------|------|----------|
| **Task plan** | `task_plan.md` | Phase breakdown, status, constraints |
| **Findings** | `findings.md` | All discovered research, system state, issues |
| **Progress** | `progress.md` | Session log, next actions |
| **Session handoff** | `SESSION_HANDOFF.md` | This file |
| **Context files** | `docs/context/` | Stack, conventions, constraints, services, learnings |
| **Project notes** | `docs/project_notes/` | Bugs, decisions (ADRs 001-023), issues, key facts |
| **Diagrams** | `docs/diagrams/` | 7 Mermaid diagrams + summary in `docs/exploration/` |
| **Plans (past)** | `docs/plans/` | base/, agent-team/, mcp-mem0-update/, product_owner/ |
| **RAG dev** | `docs/rag-dev/` | Spec, findings, edge contract, handoff — paused at A3 |
| **Briefs** | `docs/briefs/` | MCP-Mem0 fixes (4 briefs, not yet executed) |
| **Test Docker** | `test-docker/` | Validated symlink bridge experiment |
| **OpenCode backup** | `opencode-mem-backup/` | Previous system context (pre-overhaul) |
| **Source** | `src/` | MCP server, memory service, RAG pipeline |
| **Docker** | `Dockerfile`, `docker-compose.yml` | Current (old) single-container setup |

---

## 7. Installed Skills (Relevant Ones)

### LangChain/Graph (installed this session)
- `langgraph-fundamentals` — StateGraph, nodes, edges, routing
- `langgraph-persistence` — Checkpointers, per-agent state
- `langgraph-human-in-the-loop` — Approval interrupts/gates
- `langchain-architecture` — Architecture patterns (7.6K installs)
- `langchain-rag` — RAG patterns
- `langchain-fundamentals`, `langchain-dependencies`, `langchain-middleware`

### Deep Agents (installed this session)
- `deep-agents-core`, `deep-agents-orchestration`, `deep-agents-memory`

### Pre-existing
- `multi-agent-orchestration` — Delegation patterns
- `planning-with-files` — File-based planning (loaded, active)
- `project-memory` — Institutional memory
- `qdrant-vector-search`, `qdrant-search-quality`
- `python-patterns`, `async-python-patterns`, `pydantic`
- `architecture-patterns`, `mermaid-diagrams`
- `agent-pseudocode`, `create-specification`

---

## 8. Key Decisions Made This Session

| Decision | Rationale |
|----------|-----------|
| **Symlink bridge is THE filesystem access model** | Validated in test-docker/. Zero-copy, zero-host, dynamic grants without restart. |
| **Filesystem MCP → backlog** | Symlink bridge makes it redundant for bulk I/O. |
| **MVP: Implementer + Explorer** | Start minimal, expand later. Expert/architect/researcher are defined but backlog. |
| **Agents never communicate directly** | All routing through orchestrator. File-based handoffs. |
| **User handles git, not the system** | No "commit back to host" step needed. Agent writes hit shared volume, user reviews/commits. |
| **Named volumes (not bind mounts) for isolation** | Agents must never touch host. Docker volumes are the boundary. |
| **Flox per container** | Hermetic, reproducible environments. Fresh adoption. |

---

## 9. Constraints (Non-Negotiable)

- Agents **never access host filesystem** — Docker volumes only
- RTX 3080 (10GB VRAM max), 32GB RAM max
- Python 3.14+, uv package manager
- Ollama models: `llama3.1:8b`, `nomic-embed-text` (768-dim)
- Qdrant on port 6333
- Single user, no auth
- `bunx` not `npx`, `bun` not Node.js
- Port 8000 (not 8001)
- No hardcoded secrets or user IDs — env vars only
- `src/` is NOT a Python package — relative imports within packages

---

## 10. Nuances & Context for Next Agent

### Why the overhaul?
User tried Mem0, managed DBs, monolithic MCP servers — they lacked fine-grained control over individual agent flows. The vision is templates that adapt: an "expert architect" could be Python-specialist or Java-specialist based on injected context and a feedback loop.

### User's mental model
- User is the **project owner / lead software engineer** switching between projects
- User runs the Docker fleet, controls which project is active, handles git
- Agents are **tools**, not co-developers — they execute tasks in isolated workspaces
- The orchestrator is the **single point of contact** between user and agent team

### What "LangGraph-style" means
- Each agent has its own StateGraph with persisted state (learnings survive restarts)
- Orchestrator has its own StateGraph tracking session phase, agent assignments, context
- Human-in-the-loop interrupts for the 4-gate approval pipeline (Approach → Spec → Code → Review)
- **Not** LangChain chains — it's the graph-based state management pattern

### The explorer subagent gotcha
The `explorer` subagent type returns only `"complete"` or `"error"` — actual findings are written to `docs/exploration/`. General subagents return content inline. This burned us once. See LEARNINGS.md §9.

### Context file update protocol
- `docs/context/` files are mandatory read at session start
- `docs/context/LEARNINGS.md` updated with: over-reading rule, subagent behavior table, "test before you spec" principle
- `docs/context/services.md` was not read this session (permission denied — user reminded to only read what's needed)

---

## 11. Exact Next Steps

1. **Load `langgraph-fundamentals`** — understand StateGraph model before designing
2. **Load `langchain-architecture`** — container-per-agent patterns (7.6K installs, likely high-signal)
3. **Design Phase 1**: Volume topology + Docker Compose layout + Flox env manifests + Dockerfile template
4. **Present Phase 1 design for user approval** before proceeding to Phase 2
5. **Do NOT** load implementation skills (langgraph-persistence, langchain-dependencies) until ready to implement — those are for implementers

### If resuming mid-session:
- Read `task_plan.md` first (current phase, remaining phases)
- Read `findings.md` (all prior research)
- Read `progress.md` (session log)
- Read `test-docker/test1.yml` (validated architecture proof)
- Read `docs/context/LEARNINGS.md` (mandatory)
- Phase 1 is in_progress, next action = load langgraph skills + design

---

## 12. Files Modified This Session
| File | Action |
|------|--------|
| `task_plan.md` | Created, revised 3x |
| `findings.md` | Created, updated |
| `progress.md` | Created, updated |
| `SESSION_HANDOFF.md` | Created |
| `test-docker/docker-compose.yml` | Created (original), replaced by user |
| `test-docker/test1.yml` | Created (user) |
| `test-docker/Dockerfile.basetest` | Created (user) |
| `docs/context/LEARNINGS.md` | Updated (3 additions) |
| `docs/exploration/diagrams-summary.md` | Created (explorer agent) |
| `docs/exploration/plans-summary.md` | Created (explorer agent) |
| `docs/docker/volumes.md` | Read (user-added prior) |
| `docs/docker/research-v1.txt` | Read (user-added prior) |
