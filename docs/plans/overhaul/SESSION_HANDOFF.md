# SESSION HANDOFF — Agentic Container Overhaul (Session 002)

**Date:** 2026-05-08
**Status:** Phase 1 (Agent Design) complete. Phase 2 (Container & Volume Topology) next.
**Handoff to:** Next orchestrator session or human review.

---

## 1. Objective

Overhaul the local Docker setup from a single OpenCode MCP server into a **LangGraph-based multi-container agent system** powered by **Flox environments**.

- Each agent type = generic template with config-driven variations (model + skills + context injection)
- Prompts define interaction mechanics, never domain knowledge
- LangGraph for per-agent state management and the orchestrator's decision flow
- Flox per container for hermetic, reproducible environments
- **Core 5 types**: Orchestrator, System Thinker, Implementer, Auditor, Explorer
- **9 variations**: strategic_thinker, rag_thinker, architect_thinker, python_implementer, infra_implementer, code_auditor, codebase_explorer, dependency_explorer, + Orchestrator (no variation)
- Agents **never communicate directly** — orchestrator routes via file-based handoffs
- Agents **never access the host** — filesystem isolation via Docker volumes only
- Orchestrator **never reads full content** — summaries + file paths only, bubbles to user after every agent

---

## 2. What Changed This Session

### Agent Variation Framework (Solidified)
- RAG Architect absorbed into System Thinker as `rag_thinker` variation
- Architect is System Thinker variation (`architect_thinker`), not a separate type
- Code Auditor + Integration Auditor merged (context differentiates, not separate type)
- Model assignments: GLM-5.1 (orch), Qwen 3.6 Plus (thinker), DeepSeek V4 Flash (impl/expl), DeepSeek V4 Pro (auditor)
- File-based handoff protocol defined with read/write boundaries per agent type
- Each agent reads only what it needs: Thinkers never see source code, Implementers never see briefs, Auditors never see briefs

### Files Modified
| File | Action |
|------|--------|
| `.opencode/prompts/orchestrator.md` | Updated — Variation Framework, Handoff Protocol, Read/Write table |
| `.opencode/prompts/system_thinker.md` | Updated — Read/Write Boundaries, brief consumption, expanded anti-scope |
| `.opencode/prompts/implementer.md` | Updated — Read/Write Boundaries, "Never read briefs" |
| `.opencode/prompts/auditor.md` | Updated — Read/Write Boundaries, "Never read briefs" |
| `.opencode/prompts/explorer.md` | Updated — Mandatory Principles added, Read/Write Boundaries |
| `.opencode/prompts/reviewer.md` | DELETED — absorbed into Auditor |
| `.opencode/prompts/coordinator.md` | DELETED — redundant with Orchestrator |
| `.opencode/prompts/rag_architect.md` | DELETED — absorbed into System Thinker |
| `.opencode/opencode.jsonc` | Updated — models, removed rag_architect, variation names in descriptions |
| `docs/plans/overhaul/agent-variation-matrix.md` | CREATED — full variation table, flow, rationale |
| `docs/context/LEARNINGS.md` | Updated — §13, §14, §15 added |
| `docs/plans/overhaul/task_plan.md` | Updated — new phases, variation framework section |
| `docs/plans/overhaul/findings.md` | Updated — roster, variation framework, model rationale |
| `docs/plans/overhaul/progress.md` | Updated — Session 002 log |

---

## 3. Current System State (What Exists)

### Working
- **FastMCP server**: 5 memory tools (add/search/delete/sync/list) on port 8000
- **Agent team v2 designed**: 5 core types + 9 config-driven variations
- **mcp-mem0-update**: Fully complete (goal tree migration, 96 unit tests passing)
- **RAG pipeline A1+A2**: Pydantic models, edge contract (40 triples, 10 node types), chunker, embedder, Qdrant client — 82 tests pass
- **Agent prompts**: All 5 core prompts updated with Variation Framework, Read/Write Boundaries, Mandatory Principles
- **opencode.jsonc**: Models updated, rag_architect removed, variation names in descriptions
- **Symlink bridge validation**: test-docker/ proof of concept working

### Known Issues (from docs/project_notes/)
- Qdrant collections stale (1536-dim), need recreation at 768-dim
- Mem0 v3 API: `user_id` must be inside `filters` dict
- PORT=8001 still in `.env` causing 3 test failures
- Integration tests: 3/8 pass, 5 fail
- RAG paused at A3 (Graph DB integration — zero code, spec written)
- `infer` parameter not yet implemented

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

---

## 5. Agent Variation Framework

**See `docs/plans/overhaul/agent-variation-matrix.md` for full detail.**

| Variation | Base Type | Model | Skills | Context Injection |
|-----------|-----------|-------|--------|-------------------|
| orchestrator | — (primary) | glm-5.1 | planning-with-files | All docs/context/* (pointers only) |
| strategic_thinker | system_thinker | qwen-3.6-plus | sequential-thinking, create-specification | constraints, services, stack |
| rag_thinker | system_thinker | qwen-3.6-plus | qdrant-*, langchain-rag, sequential-thinking | constraints, stack, RAG specs |
| architect_thinker | system_thinker | qwen-3.6-plus | architecture-patterns, agent-pseudocode, create-specification, mermaid-diagrams, sequential-thinking | constraints, stack, conventions, brief |
| python_implementer | implementer | deepseek-v4-flash | python-expert, python-best-practices, pydantic, python-type-safety | constraints, conventions, stack, spec |
| infra_implementer | implementer | deepseek-v4-flash | context7 | constraints, stack, spec |
| code_auditor | auditor | deepseek-v4-pro | python-code-review, pytest, pytest-coverage | constraints, conventions, spec, code |
| codebase_explorer | explorer | deepseek-v4-flash | (none — built-in) | Targeted query + paths |
| dependency_explorer | explorer | deepseek-v4-flash | (none) | Targeted query + paths |

**Key principle:** Prompts stay generic. New variations = new config row, zero prompt or code changes.

---

## 6. Current Plan (task_plan.md)

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Planning & context gathering | ✅ Complete |
| 1 | Agent Design (types, variations, prompts, models) | ✅ Complete |
| 2 | Container & Volume Topology Design | Pending (next) |
| 3 | LangGraph State Management | Pending |
| 4 | Orchestrator Agent Design | Pending |
| 5 | RAG Integration (complete paused A3-A6) | Pending |
| 6 | Implementation: Container + State | Pending |
| 7 | Implementation: Orchestrator + RAG | Pending |
| 8 | Polish, tests, docs | Pending |

---

## 7. Where Everything Lives

| Resource | Path | Contents |
|----------|------|----------|
| **Task plan** | `docs/plans/overhaul/task_plan.md` | Phase breakdown, status, constraints |
| **Findings** | `docs/plans/overhaul/findings.md` | All discovered research, system state, issues |
| **Progress** | `docs/plans/overhaul/progress.md` | Session log, next actions |
| **Session handoff** | `docs/plans/overhaul/SESSION_HANDOFF.md` | This file |
| **Variation matrix** | `docs/plans/overhaul/agent-variation-matrix.md` | Full variation table, flow, model rationale |
| **Context files** | `docs/context/` | Stack, conventions, constraints, services, learnings |
| **Project notes** | `docs/project_notes/` | Bugs, decisions (ADRs 001-023), issues, key facts |
| **Diagrams** | `docs/diagrams/` | 7 Mermaid diagrams + summary |
| **Plans (past)** | `docs/plans/` | base/, agent-team/, mcp-mem0-update/, product_owner/ |
| **RAG dev** | `docs/rag-dev/` | Spec, findings, edge contract, handoff — paused at A3 |
| **Briefs** | `docs/briefs/` | MCP-Mem0 fixes (4 briefs, not yet executed) |
| **Test Docker** | `test-docker/` | Validated symlink bridge experiment |
| **Source** | `src/` | MCP server, memory service, RAG pipeline |
| **Docker** | `Dockerfile`, `docker-compose.yml` | Current (old) single-container setup |
| **Agent prompts** | `.opencode/prompts/` | orchestrator, system_thinker, implementer, auditor, explorer |

---

## 8. Exact Next Steps

1. **Phase 2: Container & Volume Topology Design** — delegate to architect_thinker (System Thinker variation with architecture-patterns + mermaid-diagrams skills)
2. Design Docker Compose layout with per-variation container specs
3. Map variation matrix to Dockerfile template + Flox manifests
4. Design context injection mechanism (JSON config file per spawn)
5. **User approval gate** before Phase 3

### If resuming mid-session:
- Read `docs/plans/overhaul/task_plan.md` first (current phase, remaining phases)
- Read `docs/plans/overhaul/findings.md` (all prior research)
- Read `docs/plans/overhaul/progress.md` (session log)
- Read `docs/plans/overhaul/agent-variation-matrix.md` (variation definitions)
- Read `docs/context/LEARNINGS.md` (mandatory — includes §13-15 on variation framework)
- Read `test-docker/test1.yml` (validated architecture proof)

---

## 9. Key Decisions Made This Session

| Decision | Rationale |
|----------|-----------|
| **RAG Architect → System Thinker variation** | Same interaction mechanics. Different skills = different variation. Avoids type proliferation. |
| **Code Auditor + Integration Auditor merged** | Same 5-check framework. Context injection per task differentiates. |
| **Architect is System Thinker variation** | "How does it fit?" is a design question. Same mechanics (wide-deep, file output, skill loading). |
| **Prompts stay generic, variations are config** | Upgrade path: containers map 1:1 to variations. No prompt changes when adding variations. |
| **Orchestrator never reads full content** | Token conservation. Orchestrator owns context direction, not content depth. |
| **GLM-5.1 for Orchestrator** | Long-horizon endurance (600+ tool calls). Won't lose user intent during deep delegation. |
| **Qwen 3.6 Plus for System Thinker** | 1M context window for whole-system reading. |
| **DeepSeek V4 Pro for Auditor** | Lowest hallucination rate. Precision for catching flaws. |
| **DeepSeek V4 Flash for Implementer/Explorer** | 15x cheaper, near-parity for standard logic and scanning. |
| **Explorer needs no skills** | Built-in tools (glob, grep, rg, git, read) cover all exploration needs. |

---

## 10. Constraints (Non-Negotiable)

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
