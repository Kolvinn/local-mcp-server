# Session 009 Handoff — Agent Architecture Redesign

**Date**: 2026-04-29
**Status**: Complete — Agent team v2 designed and configured

---

## What Was Accomplished

1. **Identified root cause of agent overlap**: Coordinator and Product Owner had ~95% shared scope. Dual primary agents fighting for user contact, goal ownership, delegation, and gate management.

2. **Designed v2 agent team** (ADR-023):
   - **Orchestrator** (primary) — single entry point. Owns goals, workflow state, delegation, 4 approval gates. Anti-scope: never designs, codes, explores, reviews.
   - **System Thinker** (spawnable template) — domain design via skill injection. Produces options (wide) + pseudocode specs (deep). Records learnings for cross-instance continuity.
   - **Implementer** (subagent) — translates pseudocode → production code. Project-agnostic. Reads `docs/context/` for project specifics.
   - **Reviewer** (subagent) — verifies code against pseudocode spec. Structural compliance, not intent inference.
   - **Explorer** (subagent) — structural analysis (dependency graphs, call chains) + file search. File-only output.

3. **Key architectural innovations**:
   - **Pseudocode handoff**: falsifiable contracts between design and implementation. No interpretation gray zone.
   - **Transparency protocol**: agents write full output to files, pass condensed summaries. Orchestrator context stays lean. User inspects anything.
   - **Three-tier context model**: baked methodology (T1) + domain context files (T2) + task delegation (T3). All agents project-agnostic.
   - **File access protocol**: `head -c 5000` threshold before Orchestrator reads directly. Source code always delegated to Explorer.
   - **Dynamic spawning**: multiple System Thinker instances for parallel analysis with different skill loads.
   - **Evolution mechanism**: session ratings + learning recordings feed improvement runs.

4. **Files created**: 5 agent prompts, 4 context files, updated opencode.jsonc.
5. **Files removed**: coordinator.md, product_owner.md, expert.md, agentic_architect.md, agent-creator.md, agent_team.md.

---

## Current State

- **Agent team v2**: Fully configured in `opencode.jsonc`. All 5 agent prompts written.
- **Context files**: `docs/context/` populated with stack, conventions, constraints, services.
- **Legacy agents**: Removed from config and disk.
- **Main project**: Memory service implementation still pending (Session 007-008 backlog).

---

## Next Steps (User's Discretion)

- **Start using the new agent team**: Begin a session with Orchestrator for memory service work.
- **Test the workflow**: Run through a full feature with all 4 gates: approach → spec → code → review.
- **Collect initial ratings**: Establish baseline for evolution mechanism.
- **Memory service work (backlog)**: Implement `infer` parameter, create live ingestion test suite.
- **Proxy pattern**: Wire up root `main.py` as proxy server, mount memory service behind it.

---

## Files Modified

- `prompts/orchestrator.md` — NEW: entry agent with file access protocol
- `prompts/system_thinker.md` — NEW: spawnable template with pseudocode spec writing
- `prompts/implementer.md` — REWRITTEN: project-agnostic, pseudocode translator
- `prompts/reviewer.md` — REWRITTEN: pseudocode compliance, file-based output
- `prompts/explorer.md` — REWRITTEN: structural analysis, file-only output
- `docs/context/stack.md` — NEW: runtime, frameworks, hardware
- `docs/context/conventions.md` — NEW: code style, naming, patterns
- `docs/context/constraints.md` — NEW: hard limits, security boundaries
- `docs/context/services.md` — NEW: available services, ports
- `opencode.jsonc` — REPLACED: v2 agent team, old agents decommissioned
- `docs/project_notes/decisions.md` — Added ADR-023
- `docs/project_notes/key_facts.md` — Updated agent team, protocols, file map
- `docs/project_notes/handoff.md` — This entry

**Date**: 2026-04-25
**Status**: In progress — blocked on implementation decisions

---

## What Was Accomplished

1. **Read all project memory** (bugs.md, decisions.md, issues.md, key_facts.md) — full context loaded
2. **Fixed `EMBEDDING_MODEL` default bug** — changed `bge-m3` → `nomic-embed-text` in `src/main.py` + `test_main.py`
3. **Updated `key_facts.md`** — corrected base image (`framework-opencode`), conda env (`dev1`), deleted `.env` file, embedding model, LLM model dependency note, Dockerfile details, test infrastructure section, proxy architecture note, infer parameter context
4. **Updated `bugs.md`** — logged EMBEDDING_MODEL default bug and stale .env references
5. **Created ADR-020** (`decisions.md`) — `infer` parameter for `add_memory`, with full trade-off analysis
6. **Created ADR-021** (`decisions.md`) — Live ingestion test architecture (11 tests, 3 memories, MCP protocol)
7. **Updated `issues.md`** — added session 007 entry, added two new priority items (infer param + live test suite)
8. **Verified 50 unit tests pass** after EMBEDDING_MODEL fix
9. **Installed project dependencies** via `uv pip install pyproject.toml --system` in conda dev1

---

## Architectural Decision Pending: Fact Extraction Responsibility

### The Core Question

**Where should fact extraction happen — on the server (local LLM) or on the agent side?**

| Approach | Fact Extraction | Local LLM Needed | Fact Quality | VRAM | Latency |
|----------|-----------------|-------------------|--------------|------|---------|
| A: Server-side infer | llama3.1:8b via infer=True | Yes (6-8GB) | Decent, not great | Heavy | 3-5s/call |
| B: Agent-side extraction | Agent model sends pre-extracted facts, infer=False | No — only embedding model (~274MB) | High | Minimal | ~100ms |
| C: Hybrid | Agent extracts, then server deduplicates via infer=True | Yes | Best (agent quality + server dedup) | Heavy | 3-5s/call |

### Why This Matters

- The primary callers of `add_memory` are LLM agents. They already understand the content.
- Making a powerful agent model pass raw text to a weaker local model for extraction is architecturally questionable.
- If default is `infer=False`, the local LLM becomes optional — dropping VRAM from ~8GB to ~300MB.
- But `infer=False` loses Mem0's automatic deduplication. Agent must handle redundancy.
- This affects: hardware requirements, deployment footprint, testing strategy, future proxy architecture.

### What's Decided

- `infer` parameter WILL be added (default `True` for backward compat)
- Both paths WILL be tested in the ingestion test suite

### What's NOT Decided

- Should the default eventually change to `False`?
- Should the LLM model be optional in deployment (only pulled if `infer=True` is needed)?
- For agent-driven workflows, should there be a "smart add" that takes pre-extracted facts and still deduplicates against existing memories?

---

## Next Steps (In Order)

1. **Implement `infer` parameter** — Add optional `infer` boolean to `add_memory` in `src/main.py` (default `True`)
2. **Create `tests/integration/` directory** — New test directory for live infrastructure tests
3. **Create live ingestion test suite** — 11 tests per ADR-021:
   - 1: Qdrant connectivity
   - 2: Ollama nomic-embed-text load
   - 3: add_memory with infer=False (global)
   - 4: search_memory by query (semantic)
   - 5: search_memory by project_id filter
   - 6: search_memory by tags filter
   - 7: add_memory with infer=True (LLM extraction)
   - 8: search_memory on infer=True data
   - 9: list_projects
   - 10: delete_memory + search confirms gone
   - 11: sync_metadata (yaml write + verify)
4. **Test data**: 3 memories total (2 global, 1 project-scoped). Minimal, proves the pipe.
5. **Cleanup**: Delete Qdrant collection after tests. Use `AGENT_ID=test_ingest` for isolation.
6. **Test execution**: Inside Docker on `internal-net`. httpx POST to `/mcp` endpoint.

---

## Test Data Design

### Global Memories (project_id=None)

| # | Content | Tags | source_user | Purpose |
|---|---------|------|-------------|---------|
| 1 | "User prefers dark theme in all development tools" | ["user-preference", "ui"] | "user" | Verify global storage |
| 2 | "Coordinator concluded that agent-side fact extraction is preferred over server-side for production" | ["conclusion", "architecture"] | "coordinator" | Verify agent conclusions |

### Project-Scoped Memory (project_id="test-project")

| # | Content | Tags | source_user | Purpose |
|---|---------|------|-------------|---------|
| 3 | "Test project uses nomic-embed-text for embeddings and stores memories in Qdrant" | ["project-context", "architecture"] | "coordinator" | Verify project filtering |

### What's NOT Tested in Phase 1

- Volume/stress testing (60 memories → phase 2)
- Current-task storage (GitHub/files, not RAG)
- sync_metadata project_id injection from .memory-context.yaml (v0.2 feature)
- Staleness checks (v0.1 feature)
- Performance benchmarks

---

## Environment State

- **Conda env**: `dev1` at `/home/dev/conda/envs/dev1`
- **Dependencies**: Installed via `uv pip install pyproject.toml --system`
- **Ollama models pulled**: `nomic-embed-text`, `llama3.1:8b`
- **Qdrant**: Running on `internal-net` at `qdrant:6333`
- **.env**: Deleted. All env vars via shell/Docker or defaults in src/main.py.

---

## Files Modified This Session

- `src/main.py` — Changed EMBEDDING_MODEL default from `bge-m3` to `nomic-embed-text`. Pending: `infer` parameter addition.
- `src/test_main.py` — Updated EMBEDDING_MODEL default assertion to `nomic-embed-text`.
- `docs/project_notes/bugs.md` — Added EMBEDDING_MODEL bug entry and .env stale reference entry.
- `docs/project_notes/decisions.md` — Added ADR-020 (infer parameter) and ADR-021 (live ingestion test).
- `docs/project_notes/issues.md` — Added session 007 entry, new priority items for infer param and live test suite.
- `docs/project_notes/key_facts.md` — Updated base image, conda env, dependencies, embedding model, LLM model note, .env status, test infrastructure section, infer parameter section, proxy architecture section, source files section.

---

# Session 008 Handoff (Side Track — Agentic Protocol)

**Date**: 2026-04-27
**Status**: Completed — main project work (infer param + test suite) still pending

---

## What Was Accomplished

1. **Identified delegation protocol violations** — Coordinator was giving implementer specific code instructions, skipping expert, not maintaining session continuity
2. **Revised `prompts/product_owner.md`** — Added approval gates (3 gates), session continuity (task_id), iterative clarification (wide before deep), "I never write code" rule, direct delegation threshold guidance
3. **Revised `prompts/expert.md`** — Added wide-before-deep protocol, tech spec file output (`docs/specs/{feature}.md`), summary-only to coordinator, session continuity
4. **Revised `prompts/implementer.md`** — Updated to receive spec file location + summary (not context dumps), reads spec file directly
5. **Removed YAML frontmatter** — Cleaned up duplicate metadata from expert/implementer prompts (opencode.jsonc is source of truth)
6. **Created `docs/specs/.gitkeep`** — Directory for future tech specs
7. **Updated `docs/project_notes/decisions.md`** — Added ADR-022 (delegation protocol fix)
8. **Updated `docs/project_notes/issues.md`** — Added session entry noting side track

---

## Side Track Summary

This session was a **side track from the main project** (live ingestion test suite). The main work from Session 007 is still pending:

- ❌ `infer` parameter not yet implemented (expert spec needed)
- ❌ Live ingestion test suite not yet created

### Why This Mattered

The coordinator (product_owner) was violating its own protocol:
- Told implementer exactly what code to write ("add `infer: bool = True` to function signature")
- Skipped expert when expert was required for architectural decisions
- Didn't use task_id for session continuity
- Gave implementer specific instructions instead of goals/constraints

If uncorrected, this would have led to: incorrect architecture, wasted implementer work, context bloat.

---

## Protocol Changes Summary

### Flow with Approval Gates

```
User → Me (goal understanding)
         ↓
       Expert (condensed options: "here are 2-3 approaches with trade-offs")
         ↓
       **USER APPROVES** ← Gate 1
         ↓
       Expert (writes tech spec to `docs/specs/{feature}.md`, sends me summary only)
         ↓
       **USER APPROVES** ← Gate 2
         ↓
       Implementer (reads spec file, writes code)
         ↓
       **USER APPROVES** ← Gate 3
         ↓
       Done
```

### Key Rules

1. **I NEVER write code** — State goals, constraints, outcomes only
2. **Expert goes wide before deep** — Condensed options first, full spec after approval
3. **Expert writes spec to file** — `docs/specs/{feature}.md`, sends me summary only
4. **I don't read the spec file** — Summary is sufficient for tracking
5. **Session continuity** — Always pass `task_id` to continue expert sessions
6. **opencode.jsonc is source of truth** — Permissions/models/descriptions live there, not in prompt files

---

## Next Steps (Back to Main Project)

1. **Implement `infer` parameter** — Follow the new protocol:
   - Call expert (with task_id) for condensed options
   - User approves approach
   - Expert writes spec to `docs/specs/infer_param.md`
   - User approves spec
   - Implementer writes code
   - User approves implementation

2. **Create live ingestion test suite** — Same protocol:
   - Expert provides options for test architecture
   - User approves
   - Expert writes spec
   - User approves
   - Implementer creates `tests/integration/` + 11 tests

---

## Files Modified This Session

- `prompts/product_owner.md` — Added approval gates section, session continuity, iterative clarification, "I never write code" rule
- `prompts/expert.md` — Added wide-before-deep protocol, spec file output, session continuity. Removed YAML frontmatter.
- `prompts/implementer.md` — Updated to receive spec file + summary. Removed YAML frontmatter.
- `docs/specs/.gitkeep` — Created specs directory
- `docs/project_notes/decisions.md` — Added ADR-022 (delegation protocol fix)
- `docs/project_notes/issues.md` — Added side track session entry