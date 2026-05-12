# Plans Survey

**Date:** 2026-05-12  
**Scope:** All `.md` files under `docs/plans/`  
**Agent:** Explorer (read-only survey)

---

## Summary Table

| # | File | Category | Relevant To | Action | Status |
|---|------|----------|------------|--------|--------|
| 1 | `overhaul/MASTER_STATUS.md` | ACTIVE_PLAN | agent_framework | KEEP | Latest master context |
| 2 | `overhaul/SESSION_HANDOFF_006.md` | ACTIVE_PLAN | agent_framework | KEEP | Latest session handoff |
| 3 | `overhaul/SESSION_HANDOFF.md` | SUPERSEDED | agent_framework | CONDENSE | Superseded by _006 |
| 4 | `overhaul/task_plan.md` | ACTIVE_PLAN | agent_framework | KEEP | Phase tracking (Phases 3-8 pending) |
| 5 | `overhaul/progress.md` | ACTIVE_PLAN | agent_framework | KEEP | Historical session log |
| 6 | `overhaul/findings.md` | ACTIVE_PLAN | agent_framework | KEEP | Technical findings & decisions |
| 7 | `overhaul/architecture_chat.md` | SCRATCH | agent_framework | CONDENSE | Raw chat transcript, research |
| 8 | `overhaul/docker_architecture_chat.md` | SCRATCH | agent_framework | CONDENSE | Raw chat transcript on docker |
| 9 | `overhaul/agent-variation-matrix.md` | ACTIVE_PLAN | both | KEEP | Active reference for agent types |
| 10 | `overhaul/bootstrap_project.sh` | SUPERSEDED | agent_framework | DELETE | Superseded by controller container |
| 11 | `overhaul/test_compose.md` | SCRATCH | agent_framework | DELETE | Draft compose snippet, not a plan |
| 12 | `base/task_plan.md` | COMPLETED | app | KEEP | Historical — base MCP architecture design |
| 13 | `base/progress.md` | COMPLETED | app | KEEP | Historical session log |
| 14 | `base/findings.md` | COMPLETED | app | KEEP | Historical findings |
| 15 | `agent-team/task_plan_agents.md` | SUPERSEDED | both | KEEP | Superseded by overhaul container model |
| 16 | `agent-team/progress_agents.md` | SUPERSEDED | both | KEEP | Historical |
| 17 | `agent-team/findings_agents.md` | SUPERSEDED | both | KEEP | Historical research on OpenCode agents |
| 18 | `product_owner/task_plan.md` | COMPLETED | app | KEEP | Design completed, implementation pending |
| 19 | `product_owner/progress.md` | COMPLETED | app | KEEP | Design session log |
| 20 | `product_owner/findings.md` | COMPLETED | app | KEEP | Design findings |
| 21 | `product_owner/SPEC.md` | COMPLETED | app | KEEP | Full agent spec (ready to create) |
| 22 | `product_owner/PO_trim.md` | COMPLETED | app | KEEP | Trimmed agent prompt version |
| 23 | `mcp-mem0-update/task_plan.md` | COMPLETED | app | KEEP | All phases done, 96 tests pass |
| 24 | `mcp-mem0-update/progress.md` | COMPLETED | app | KEEP | Session log |
| 25 | `mcp-mem0-update/findings.md` | COMPLETED | app | KEEP | Technical findings |
| 26 | `mcp-mem0-update/SPEC.md` | COMPLETED | app | KEEP | Full pseudocode spec |
| 27 | `mcp-mem0-update/SESSION_SUMMARY.md` | COMPLETED | app | KEEP | Completion summary |
| 28 | `mcp-mem0-update/impl_brief_phase1.md` | COMPLETED | app | CONDENSE | Implementation brief, historical |
| 29 | `mcp-mem0-update/impl_brief_phase2.md` | COMPLETED | app | CONDENSE | Implementation brief, historical |
| 30 | `mcp-mem0-update/impl_brief_phase3.md` | COMPLETED | app | CONDENSE | Implementation brief, historical |
| 31 | `mcp-mem0-update/impl_brief_phase5.md` | COMPLETED | app | CONDENSE | Implementation brief, historical |
| 32 | `thought-graph/essential_context.md` | COMPLETED | both | KEEP | Design session context |
| 33 | `thought-graph/essential_learnings.md` | COMPLETED | both | KEEP | Design session learnings |
| 34 | `thought-graph/session_summary.md` | COMPLETED | both | KEEP | Design session summary |
| 35 | `litellm-langchain-integration.md` | SCRATCH | app | KEEP | Brief plan, not implemented |

---

## Detailed Findings (per subdirectory)

### overhaul/ (11 files) — ACTIVE PLAN: Agentic Container Overhaul

**Purpose:** Complete redesign of the system from an OpenCode-based MCP server into a distributed, LangGraph-based multi-container agent system. Each agent runs in its own Docker container with Flox environments, isolated volumes, and ACP communication.

**Current status:** Active. Session 006 was the most recent (2026-05-12). Phases 0-2.5 are complete. Phases 3-8 are pending. Code for the controller container, schema, and validators is built but untested against real Docker.

**All files reference the container system (agent_framework)** except `architecture_chat.md` which is a raw research transcript.

**Key files:**

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **MASTER_STATUS.md** | Single source of truth: architecture, component statuses, protocols, constraints, reference map. 255 lines. | **READ THIS FIRST** for any work on the container overhaul. |
| **SESSION_HANDOFF_006.md** | Session 006 handoff — major pivot from static bootstrap script to dynamic controller container. Documents what was built (schema, validators, controller Python code) and what remains (Dockerfile, agent entrypoint, testing). | **Most recent handoff.** Supersedes SESSION_HANDOFF.md. |
| **SESSION_HANDOFF.md** | Session 005 handoff — bootstrap system fully specified (6 spec files). | Superseded by _006. Contains research on LangChain/Deep Agents integration chain that may still be useful. |
| **task_plan.md** | Phase breakdown: 0-8 phases. Phases 0-2.5 complete, 3-8 pending. Lists agent variation framework, constraints, error log. | Core tracking document. Next steps: Phase 3 LangGraph State Management. |
| **progress.md** | Session-by-session log (Sessions 001-003). Documents discoveries, failures, and learnings. | Historical reference for architecture decisions. |
| **findings.md** | Technical findings: current system state, known issues, ADRs, validated symlink bridge, model rationale, agent roster. | Good reference for understanding the "before" state and design decisions. |
| **architecture_chat.md** | Raw research transcript: model selection for agent roles, system design discussion. 198 lines. | SCRATCH — chat log. Could be condensed/removed once decisions are captured elsewhere. |
| **docker_architecture_chat.md** | Extensive transcript (909 lines) on Docker architecture evolution: from basic compose → socket proxy → governance MCP container → dynamic manifest pattern. | SCRATCH — very long raw chat. Many design iterations that are now superseded by the controller container model. Valuable for understanding design journey but not an active plan. |
| **agent-variation-matrix.md** | Approved matrix: 5 core types, 9 variation profiles with model assignments, skill injection, file-based handoff protocol, read/write boundaries. 141 lines. | **Active reference.** Feeds directly into container topology design. |
| **bootstrap_project.sh** | Superseded bash bootstrap script (144 lines). Creates volumes, generates compose file. | **SUPERSEDED** by controller container. Can be deleted. |
| **test_compose.md** | Draft docker-compose snippet (29 lines). Appears to be a test/scratch file. | SCRATCH — Not a real plan. Can be deleted. |

---

### base/ (3 files) — COMPLETED: Mem0 MCP Server Architecture (Original)

**Purpose:** Initial planning phase for the dual-layer memory MCP server (Mem0 vector + local metadata files). Designed hexagonal architecture, metadata schema, staleness validation, and 5-phase plan.

**Current status:** Planning complete. This was the "base" architecture design that informed the actual implementation. The implementation itself happened in later sessions.

**Relevant to:** App MCP server (not the container system).

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **task_plan.md** | 5-phase plan for MCP server architecture design. All phases marked complete. 95 lines. | Key decisions: dual-layer memory, hexagonal architecture, YAML metadata, on-retrieval validation, 30-day staleness window. |
| **progress.md** | Session log: Phase 0-1 planning and agent team config. | Also contains 5-question reboot check and handoff notes. |
| **findings.md** | Technical findings: Mem0 SDK capabilities analysis, existing stub problems, hexagonal architecture mapping, technical decisions. | Useful reference for Mem0 API patterns. |

---

### agent-team/ (3 files) — SUPERSEDED: Agent Team Architecture

**Purpose:** Design and implementation of a 5-agent team for OpenCode (coordinator, expert, explorer, implementer, reviewer) with 3-layer delegation, user approval gates, and skill injection.

**Current status:** Phases 1-3 mostly complete (agent config created, prompts written, opencode.jsonc updated). Phases 4-7 pending. However, the overhaul effort supersedes this by moving from OpenCode subagents to Docker containers. The agent **concepts** (explorer, implementer, etc.) live on in the container model but the OpenCode-specific implementation is being replaced.

**Relevant to:** Both — the agent type concepts feed into the container system, but the OpenCode configuration files are app-specific.

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **task_plan_agents.md** | 7-phase plan for designing an OpenCode multi-agent team. Includes agent config specs, delegation mechanisms, plugin evaluation. 119 lines. | Key decisions: 5 agents, 3-layer delegation, Task tool for delegation, all-mode expert, subagent-mode implementer. |
| **progress_agents.md** | Session log: agent team design and configuration. Handoff notes for next session. 124 lines. | Notes that expert delegation was tested and working. |
| **findings_agents.md** | Comprehensive research: OpenCode agent config, CLI, Server API, SDK, plugin architecture, ecosystem plugins, delegation comparison. 310 lines. | Valuable reference for OpenCode capabilities. Could inform future decisions even if the specific plan is superseded. |

---

### product_owner/ (5 files) — COMPLETED (Design): Product Owner Agent

**Purpose:** Design a `product_owner` agent — a strategic orchestration layer that owns the "why" for user context and project direction. Project-agnostic, delegates everything, acts as single point of contact.

**Current status:** Design complete (Phases 1-5 done). SPEC.md has full agent specification ready for creation. Phases 6-7 (review, final spec) were never completed. The agent was never actually created in opencode.jsonc.

**Relevant to:** App (OpenCode agent design).

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **task_plan.md** | 7-phase plan for designing a product_owner agent. 98 lines. | Clarifies relationship to coordinator (replaces but keeps for backward compat), aggressive delegation, project-agnostic design. |
| **progress.md** | Session log. 47 lines. | Design completed in one pass. User review pending. |
| **findings.md** | Extensive findings: comparison with coordinator, ownership vs delegation categories, mental model, write delegation heuristic. 162 lines. | Good reference for the strategic/tactical distinction. |
| **SPEC.md** | Full agent spec: system prompt, personality, core responsibilities, delegation rules, output format, edge cases, interaction model. 339 lines. | **Ready-to-use agent spec.** If the product_owner agent is still desired, this spec can be used to create it. |
| **PO_trim.md** | Trimmed version of SPEC.md (243 lines) — removed some verbosity, kept core content. | Streamlined version of the same agent spec. |

---

### mcp-mem0-update/ (9 files) — COMPLETED: Goal Tree → Mem0 Migration

**Purpose:** Replace standalone `goal_trees.py` (raw Qdrant/Ollama) with Mem0-backed goal-tree tools inside `src/main.py`. 5 new MCP tools (add/search/get/update/delete goal node) sharing the existing `memory_client`.

**Current status:** **Fully completed.** All 5 phases done. 96 unit tests pass. Files backed up. Integration test script created. `goal_trees.py` deleted.

**Relevant to:** App MCP server.

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **task_plan.md** | 5-phase plan for the migration. 75 lines. | Metadata schema, tool interfaces, proxy config, .env fixes, tests. |
| **progress.md** | Planning phase log. 51 lines. | Architecture analysis and design phase. |
| **findings.md** | Technical findings: current architecture, Mem0 API reference, filter syntax, port/transport details. 102 lines. | Good Mem0 API reference. |
| **SPEC.md** | Complete pseudocode spec with metadata schema, all 5 tool algorithms, Pydantic models, acceptance criteria, test strategy. 645 lines. | **Excellent detailed spec.** Kept as reference for future Mem0 work. |
| **SESSION_SUMMARY.md** | Completion summary: 96 tests passing, files modified, bug fixed. 51 lines. | Quick reference: "it's done." |
| **impl_brief_phase1.md** | Implementation brief for Phase 1 — add 5 tools to main.py. 69 lines. | Historical. Work is done. |
| **impl_brief_phase2.md** | Implementation brief for Phase 2 — update proxy config. 47 lines. | Historical. Work is done. |
| **impl_brief_phase3.md** | Implementation brief for Phase 3 — fix .env. 41 lines. | Historical. Work is done. |
| **impl_brief_phase5.md** | Implementation brief for Phase 5 — unit + integration tests. 82 lines. | Historical. Work is done. |

---

### thought-graph/ (3 files) — COMPLETED: Orchestrator Thought Graph Design Session

**Purpose:** Design session for the orchestrator's "thought graph" — a persistent, cross-session project brain that the orchestrator builds, queries, and modifies. Core philosophy: WIDE before DEEP.

**Current status:** Design session complete. 7 mermaid diagrams created in `docs/diagrams/`. Active version: v5 (session-scope aware). Research on LangSmith trace granularity completed. Design feeds into Phase 3 (LangGraph State Management) of the container overhaul.

**Relevant to:** Both — the thought graph concept is about orchestrator behavior which spans both the current OpenCode setup and the future container system.

| File | 1-2 Sentence Description | Notes |
|------|--------------------------|-------|
| **essential_context.md** | Context doc for the design session: session rules, active diagram reference, key external references, skills loaded. 42 lines. | Not a "plan" — it's a session briefing document. |
| **essential_learnings.md** | Learnings from the design session: Mermaid config format, design decisions, node taxonomy evolution, scope checking. 26 lines. | Valuable design decisions captured here. |
| **session_summary.md** | Summary of what was designed: node taxonomy (Concept, Question, OptionNode, Option, Static), flow stages (Scope Check → PRE-STAGE → WIDE → DEEP → SYNTHESIZE → GATE → Session End). 74 lines. | Best overview of the thought graph design. Feeds into Phase 3 of overhaul. |

---

### litellm-langchain-integration.md (1 file) — SCRATCH

**Purpose:** Brief plan to replace direct OpenCode upstream calls with LiteLLM as a unified routing/proxy layer for LangChain integration.

**Current status:** Not implemented (as far as can be determined). The plan is only ~137 lines with configuration examples. No progress or findings files exist. The `test_langchain.py` file exists but this plan was never formally tracked.

**Relevant to:** App (LangChain integration).

**Notes:** This is a standalone scratch plan. It proposes setting up LiteLLM config, modifying a test file, and testing failover. The LiteLLM integration could still be relevant as a bridge between the current system and the container overhaul, since LiteLLM provides routing that the controller container might eventually need.

---

## Notable Observations

### 1. Two parallel planning tracks exist
- **Container system overhaul** (`overhaul/`): Active, ongoing. Replaces the entire infrastructure.
- **App MCP server** (`base/`, `agent-team/`, `mcp-mem0-update/`, `product_owner/`, `litellm-langchain-integration.md`): Mostly completed or superseded by the overhaul.

### 2. The overhaul supersedes several earlier plans
The agent-team OpenCode subagent model is being replaced by Docker containers. The bash bootstrap script is replaced by the controller container. The product_owner agent design was never implemented in the OpenCode config.

### 3. Most plans are "completed" in terms of design
The planning-heavy workflow means many directories are design documents that were fully specified but whose implementation was either completed (mcp-mem0-update) or deferred (product_owner, agent-team phases 4-7).

### 4. No circular dependencies between plan files
The dependency chain is linear: base → mcp-mem0-update (app features) and agent-team → overhaul (agent infrastructure). The thought-graph and product_owner are side-branches.

### 5. Files that could be cleaned up
- `overhaul/bootstrap_project.sh` — Superseded by controller container. Safe to delete.
- `overhaul/test_compose.md` — Draft snippet, not a real plan. Safe to delete.
- `overhaul/architecture_chat.md` — Chat log, could be condensed into learnings.
- `overhaul/docker_architecture_chat.md` — Very long chat log (909 lines), could be condensed.
- `mcp-mem0-update/impl_brief_phase*.md` — Implementation briefs for completed work. Could be condensed.
- `overhaul/SESSION_HANDOFF.md` — Superseded by _006. Could be condensed/archived.

---

## Reference: File Counts by Status

| Category | Count | Directories |
|----------|-------|-------------|
| ACTIVE_PLAN | 6 files | overhaul/ (MASTER_STATUS, SESSION_HANDOFF_006, task_plan, progress, findings, agent-variation-matrix) |
| COMPLETED | 16 files | base/ (3), product_owner/ (5), mcp-mem0-update/ (5+summary), thought-graph/ (3) |
| SUPERSEDED | 5 files | overhaul/SESSION_HANDOFF, overhaul/bootstrap_project.sh, agent-team/ (3) |
| SCRATCH | 4 files | overhaul/architecture_chat, overhaul/docker_architecture_chat, overhaul/test_compose, litellm-langchain-integration.md |
