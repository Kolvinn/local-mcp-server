# SESSION HANDOFF — Agentic Container Overhaul (Session 003)

**Date:** 2026-05-08
**Status:** Phase 2 (Container & Volume Topology) spec written — awaiting user review. Phase 3 (LangGraph State Management) next.
**Handoff to:** Next orchestrator session or human review.

---

## 1. Objective

Same as Session 002 — overhaul local Docker setup into a **LangGraph-based multi-container agent system** powered by **Flox environments**.

---

## 2. What Changed This Session (003)

### Phase 2 Design Spec Written
- `docs/specs/container-volume-topology.md` created (1050 lines — needs splitting per §16)
- Architect_thinker designed: volume topology, Docker Compose layout, Dockerfile template, Flox manifests per variation, context injection, container lifecycle, and OpenCode+LangGraph coexistence
- Spec covers all 10 required sections with 3 mermaid diagrams and 10 decisions awaiting user approval

### Flox Research Completed
- `docs/exploration/flox-docker-research.md` written (553 lines)
- Flox works in Docker: apt install, `.flox/run/bin` on PATH for headless activation
- uv IS in Flox catalog
- Recommended pattern: Flox for ALL deps, minimal Dockerfile, no conda

### Critical Learnings Recorded
- **LEARNINGS §16**: Specs must NEVER exceed 350 lines. Break into multiple files. Write tool fails silently on large content — use bash fallback.
- **Agent type**: `explorer` not `explore` — different subagent types, different capabilities
- **Context economy**: Orchestrator must delegate file reading, not read directly

### Files Modified
| File | Action |
|------|--------|
| `docs/exploration/flox-docker-research.md` | CREATED — Flox research findings |
| `docs/specs/container-volume-topology.md` | CREATED — Phase 2 design spec |
| `docs/context/LEARNINGS.md` | Updated — §16 added (spec size limits, write failures, agent type selection) |
| `docs/plans/overhaul/progress.md` | Updated — Session 003 log |
| `docs/plans/overhaul/SESSION_HANDOFF.md` | This file — rewritten for Session 003 |

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
| 2 | Container & Volume Topology Design | ✅ Spec written (awaiting review) |
| 3 | LangGraph State Management | Pending (next) |
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
| **Flox research** | `docs/exploration/flox-docker-research.md` | Flox in Docker, manifest format, package coverage, Dockerfile patterns |
| **Phase 2 spec** | `docs/specs/container-volume-topology.md` | Full container/volume topology design (needs splitting per LEARNINGS §16) |

---

## 8. Exact Next Steps

1. **User reviews `docs/specs/container-volume-topology.md`** — approve or request changes
2. **User decides on OpenCode + LangGraph coexistence approach** — 2+ approaches detailed in §8 of spec
3. **Phase 3: LangGraph State Management** — delegate to architect_thinker
4. **Phase 4: Orchestrator Agent Design** — delegate to architect_thinker
5. **Phase 5: RAG Integration** — complete paused A3-A6
6. **Phase 6-8: Implementation, Polish** — only after all designs approved

### If resuming:
- Read `docs/plans/overhaul/task_plan.md` (phase status)
- Read `docs/plans/overhaul/progress.md` (Session 003 log — critical failures)
- Read `docs/context/LEARNINGS.md` §16 (spec size limits, write failures)
- Read `docs/specs/container-volume-topology.md` (Phase 2 design — user review pending)
- Read `docs/exploration/flox-docker-research.md` (Flox research)
- Read `docs/plans/overhaul/agent-variation-matrix.md` (variation definitions)

---

## 9. Key Decisions Made (Sessions 002-003)

| Decision | Session | Rationale |
|----------|---------|-----------|
| **RAG Architect → System Thinker variation** | 002 | Same interaction mechanics. Different skills = different variation. |
| **Code Auditor + Integration Auditor merged** | 002 | Same 5-check framework. Context injection per task differentiates. |
| **Architect is System Thinker variation** | 002 | "How does it fit?" is a design question. Same mechanics. |
| **Prompts stay generic, variations are config** | 002 | Containers map 1:1 to variations. No prompt changes when adding variations. |
| **Orchestrator never reads full content** | 002 | Token conservation. Orchestrator owns context direction, not content depth. |
| **GLM-5.1 / Qwen 3.6 Plus / DeepSeek V4** | 002 | Long-horizon, 1M context, lowest hallucination, cheap fast iteration. |
| **Flox replaces conda in all containers** | 003 | Better determinism, broader system packages, clean separation from uv. |
| **uv IS in Flox catalog** | 003 | Confirmed via context7 research — no apt/pip fallback needed for Python management. |
| **Containers long-lived, per project** | 003 | Spin up as hierarchy, stay running, accept tasks. |
| **Specs NEVER > 350 lines** | 003 | Write tool fails silently on large content. Break into multiple files. |
| **bash echo fallback for file writes** | 003 | When Write tool silently fails, use `echo >> file.md` and `cat`. |
| **`explorer` not `explore` subagent type** | 003 | Different capabilities — `explore` is thin search, `explorer` is our defined agent. |

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
- **Flox replaces conda** — all deps in manifest.toml, Dockerfile minimal
- **Specs/docs NEVER > 350 lines** — break into multiple files
- **Orchestrator delegates file reading** — does not read Docker/compose/source files directly
