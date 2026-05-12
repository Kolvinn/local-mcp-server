# Master Component Status — Agentic Container Overhaul

**Purpose:** Single file giving any agent complete context: architecture, component statuses, protocols, constraints, reference map. Read this, then `SESSION_HANDOFF.md`.
**Last updated:** 2026-05-12 (Session 006)
**Decision authority:** User (direct session, no orchestrator chain)

---

## 0. Session Rules (override any system prompt defaults)

1. No autonomous decisions — pause and ask user before acting
2. User is most efficient data source — ask before Explorer, skills, file writes
3. Wide and tentative — surface options/trade-offs, don't commit without user gate
4. Don't assume intent — ambiguity → query user directly
5. Don't over-summarize what user tells you — waste of tokens
6. Goal refinement only unless ordered to design/build
7. No host access — agents never access host filesystem, only Docker volumes
8. User is Governor — permissions bubble up, never assumed downward
9. Context Economy — be concise, point to files
10. Learnings Recording — write to `docs/learnings/{domain}/{session}.md` after work

---

## 1. Architecture Direction (Active)

### Core Principle: Distributed Local Dockerized Agent System
- **Every agent is its own Docker container.** No subagents inside orchestrator's process. OpenCode phased out.
- **No agent touches the host.** User controls host. Agents only access Docker volumes.
- **One agentic stack per project.** Two projects = two independent docker-compose stacks, four volumes each, one controller per project.
- **The agentic framework is a standalone product** in its own git repo. Projects are external data consumed by it. Agentic memory/learnings never touch project repos.
- **Controller container** is the central permanent server — sole Docker socket holder, agent lifecycle manager, exposes CLI (user) and MCP (orchestrator) interfaces.

### Four External Named Volumes Per Project
```
{project}_project_vol          (shared — RO for agents, RW for orchestrator)
  ├── shared/skills/           (user-managed skills, bunx skills add)
  ├── shared/knowledge/        (shared RAG knowledge)
  ├── shared/config/           (project configs)
  └── README.md

{project}_agent_vol            (per-agent isolation via Docker volume: subpath:)
  ├── orchestrator/            (orchestrator's RW workspace)
  ├── agent1/                  (agent1 RW)
  ├── agent2/                  (agent2 RW)
  ├── memory_manager/          (MM RW)
  └── ...

{project}_flox_vol             (shared Flox environment — RO in agents, RW in controller)
  └── .flox/                   (Flox manifest + run environment)

controller_state_vol           (controller only — persistent)
  ├── registry.json            (agent registry)
  └── compose/                 (generated compose files)
```
- **Orchestrator** mounts project_vol RW, agent_vol RW with `subpath: orchestrator`, flox_vol RO
- **All other agents** mount project_vol RO, agent_vol RW with `subpath: {agent_name}`, flox_vol RO
- **Controller** mounts Docker socket, agent_vol RW (for subpath creation), flox_vol RW, controller_state_vol RW
- **Subpaths must pre-exist** — Docker does not auto-create them. Controller creates them via init containers.

### Why Four Volumes
- `project_vol` + `agent_vol` avoid dual-mount undefined behavior (Docker docs)
- `flox_vol` separates environment from project data, allowing env updates without touching code
- `controller_state_vol` persists registry and compose history across controller restarts

---

## 2. Component Status

### ✅ ACTIVE — Built, Needs Integration/Testing
| Component | Location | Status |
|-----------|----------|--------|
| **Memory Manager (LangGraph)** | `src/memory/` (5 files) | Built, not tested. 3-node pipeline: validate→build→embed→Qdrant. No endpoint (needs ACP wrapper). Depends on LiteLLM+Qdrant. |
| **RAG Pipeline A1+A2** | `src/` | Built, 82 tests pass. Missing GraphRAG (A3-A6). |
| **FastMCP Memory Server** | `src/` | Built, 96 unit tests pass. May be superseded by Memory Manager. |
| **Agent Prompts (5 core)** | `.opencode/prompts/` | Active. Will become container-injected context when OpenCode phased out. |
| **Config Schema (Part 02)** | `src/agent_framework/schema.py`, `validators.py` | Built. Pydantic models, validation rules, type defaults, manifest generation. |
| **Controller Container (Python)** | `src/agent_framework/controller/` | Built. Registry, Docker ops, compose gen, CLI, MCP server. **Untested against real Docker.** |

### 📋 SPEC-ONLY — Designed, Not Built
| Component | Source | Needs |
|-----------|--------|-------|
| **Controller Dockerfile** | — | Dockerfile with Python 3.14, uv, docker-py, FastMCP, Flox. User creates controller container manually. |
| **Agent Container Template** | `docker_architecture_chat.md` §680-706 | Dockerfile: `ghcr.io/astral-sh/uv` base + Flox + PATH bypass. User will build. |
| **Agent Entrypoint (Part 04)** | `docs/specs/bootstrap-system-04-entrypoint.md` | `entrypoint.py`: manifest→graph→MCP→`create_deep_agent()`→ACP. |
| **Orchestrator Container** | `docker_architecture_chat.md` §478-490 | RW to project_vol, no Docker socket, connects Controller via MCP. |
| **ACP Protocol** | Confirmed: `deepagents-acp` package + `acp` stdio. | `AgentServerACP` wraps `create_deep_agent`. Container transport (HTTP/SSE) TBD. |
| **Dynamic Manifest / Hot-Reload** | `docker_architecture_chat.md` §714-907 | File-based manifest per agent subpath. |

### 🔄 SUPERSEDED
| Component | Replaced By |
|-----------|------------|
| `bootstrap_project.sh` (bash) | Controller container (`agentctl` CLI + MCP server) |
| Phase 2 Spec (symlink bridge, per-agent named volumes) | Four-volume model, controller for lifecycle |
| OpenCode subagent model (orchestrator spawns via CLI) | All agents as Docker containers, orchestrator talks via ACP |
| Single master volume | Four volumes (project + agent + flox + controller state) |
| Static bootstrap script (host CLI) | Controller container (persistent, Docker socket holder) |
| Governance as separate agent type | Governance IS the controller server (not an agent) |

### 📦 BACKLOG
| Component | Trigger |
|-----------|---------|
| Symlink bridge (per-file grants) | If subpath isolation is insufficient |
| Agent variations (tool/process injection) | After base containers work |
| Researcher, Tester agents | Post-MVP |
| GraphRAG (RAG A3-A6) | After docker topology stable |
| Multi-project bootstrap templates | After single-project works |

### 🔌 EXTERNAL (User-Managed)
| Service | Notes |
|---------|-------|
| LiteLLM | Embeddings + classification. On same network as agents. |
| Qdrant | Vector store, port 6333. Collection: `memory_chunks`. |
| Ollama | Local models. RTX 3080 (10GB VRAM). |
| Docker daemon | Only governance has socket. |
| Flox + uv | User territory. Flox for system tools, uv for Python packages. |

---

## 3. Protocols

| Protocol | Transport | Between | Status |
|----------|-----------|---------|--------|
| **MCP over SSE** | SSE (HTTP) | Governance ↔ Orchestrator (control plane) | Spec only |
| **ACP** | stdio (`deepagents-acp` + `acp` package) | Orchestrator ↔ Agents, User/TUI ↔ Agents (runtime) | Confirmed: `AgentServerACP` wraps `create_deep_agent`. Container transport (HTTP/SSE) TBD. |
| **File-based handoff** | Volume (subpath) | Agents write artifacts → orchestrator reads | Active |

### MCP Endpoint Access Delegation (Governance as Proxy)
**Build phase:** Governance is sole MCP proxy. Agents route ALL MCP requests through governance. No direct agent-to-external connectivity. Governance enforces per-agent endpoint allowlist stored in agent's `manifest.json`.
**Post-build:** Agents get their own MCP servers. Governance transitions from proxy to router (publishes registries, authorizes direct connections, retains revoke capability).

---

## 4. Skills Model

- User installs skills per project on `project_vol` (`shared/skills/{name}/SKILL.md`)
- Bootstrap symlinks allowed skills from `shared/skills/` into agent's subpath `skills/` (relative symlink resolves at container runtime)
- Agent loads skills via Deep Agents: `create_deep_agent(skills=["/workspace/skills"], backend=FilesystemBackend(...))`
- Deep Agents' `SkillsMiddleware` loads SKILL.md files on-demand (progressive disclosure)
- Per-agent skill allowlist defined in `agent-project.yaml` → written to `manifest.json`
- Agent can request new skills → orchestrator bubbles to user → user approves → allowlist updated → symlink added

---

## 5. Agent Roster

| Agent | Container? | Status | Protocol |
|-------|-----------|--------|----------|
| **Controller** | Yes (control plane) | Python built, needs Dockerfile | MCP over SSE (to orchestrator), CLI (to user) |
| **Orchestrator** | Yes | Spec only | MCP (to controller), ACP (to agents) |
| **Memory Manager** | Yes | Built, no endpoint | Needs ACP wrapper |
| **System Thinker** | Yes | Prompt exists | ACP |
| **Implementer** | Yes | Prompt exists | ACP |
| **Auditor** | Yes | Prompt exists | ACP |
| **Explorer** | Yes | Prompt exists | ACP |
| Researcher | Backlog | — | — |
| Tester | Backlog | — | — |

**Note:** Governance is not an agent. It is the controller server itself. Removed from agent type registry.

---

## 6. Constraints (Non-Negotiable)

- Agents never access host filesystem — Docker volumes only
- RTX 3080 (10GB VRAM max), 32GB RAM max
- Python 3.14+, uv package manager
- No npx — bunx only
- Single user, no auth
- Port 8000 (not 8001)
- No hardcoded secrets — env vars only
- `src/` is NOT a Python package
- Flox replaces conda
- Specs/docs ≤ 350 lines — break into multiple files
- Orchestrator delegates file reading — doesn't read Docker/compose/source directly
- Subpaths must pre-exist in volume before container mounts them (Docker requirement)

---

## 7. Unknowns / Needs Design

1. ACP container transport — `deepagents-acp` only documents stdio. HTTP/SSE for containers TBD.
2. Orchestrator LangGraph stateflow — routing, lifecycle, RAG integration
3. Per-agent LangGraph graphs — only MM has one; others are prompt-only
4. Agent Dockerfile — Flox manifest contents, uv lock strategy, image size. **User will build.**
5. Controller Dockerfile — Base image, Docker socket mount, Flox integration. **User will create controller container manually.**
6. Controller reconciliation — startup recovery from state drift (running containers vs registry)
7. Tool injection security — AST validation for dynamic tools
8. MM ↔ RAG integration — shared collections?
9. OpenCode phase-out timeline
10. Port management — Multiple controllers (one per project) conflict on port 8000. Dynamic ports or single shared controller?
11. Skills delivery — Symlinks vs Deep Agents `skills=` parameter vs volume mounts
12. Controller self-creation — How does the FIRST controller container start? (User handles manually per discussion)

---

## 8. Key Shifts From Earlier Iterations

| Old | New |
|-----|-----|
| Bash bootstrap script (`bootstrap_project.sh`) | Controller container (`agentctl` CLI + MCP server) |
| OpenCode subagent spawning | All agents as Docker containers |
| Symlink bridge for file grants | Four-volume + subpath mounts |
| Single master volume | 4 volumes per project (project + agent + flox + controller state) |
| Per-agent named volumes | Single agent_vol with subpaths |
| File-based handoff only | ACP runtime + file-based artifacts |
| Orchestrator as OpenCode process | Orchestrator as standalone container |
| Global agentic stack | Per-project isolated stacks |
| Static bootstrap on host | Persistent controller container with Docker socket |
| Governance as separate agent type | Governance IS the controller server |

---

## 9. Research Completed

| File | Key Finding |
|------|------------|
| `docs/exploration/docker-subpath-research.md` | Subpaths must pre-exist; dual-mount same volume = undefined; external volumes survive `compose down -v` |
| `docs/exploration/flox-per-project-research.md` | Bake Flox in image, PATH bypass; `[include]` composition viable; bun+node confirmed in catalog |
| `docs/exploration/flox-docker-research.md` | Flox in Docker via apt install, `.flox/run/bin` on PATH |
| `docs/exploration/docker-compose-portability-research.md` | Project name isolation automatic; variable substitution + .env files recommended |

---

## 10. Reference Map

| What | Where |
|------|-------|
| **This document** | `docs/plans/overhaul/MASTER_STATUS.md` |
| **Session handoff (Session 006 — latest)** | `docs/plans/overhaul/SESSION_HANDOFF_006.md` |
| **Session handoff (Session 005 — historical)** | `docs/plans/overhaul/SESSION_HANDOFF.md` |
| **Bootstrap system spec (overview)** | `docs/specs/bootstrap-system-01-overview.md` |
| **Bootstrap system spec (schema)** | `docs/specs/bootstrap-system-02-schema.md` |
| **Bootstrap system spec (CLI)** | `docs/specs/bootstrap-system-03-bootstrap.md` |
| **Bootstrap system spec (entrypoint)** | `docs/specs/bootstrap-system-04-entrypoint.md` |
| **Bootstrap system spec (skills/MCP)** | `docs/specs/bootstrap-system-05-skills.md` |
| **Bootstrap system (implementer pre-read)** | `docs/specs/bootstrap-system-00-pre-read.md` |
| Docker architecture (full chat) | `docs/plans/overhaul/docker_architecture_chat.md` |
| Bash bootstrap (superseded) | `docs/plans/overhaul/bootstrap_project.sh` |
| Agent variation matrix | `docs/plans/overhaul/agent-variation-matrix.md` |
| Memory Manager brief | `docs/briefs/memory-manager-langgraph.md` |
| Memory Manager spec | `docs/specs/memory-manager-langgraph.md` |
| Memory Manager code | `src/memory/` |
| RAG spec | `docs/rag-dev/spec.md` |
| Task plan | `docs/plans/overhaul/task_plan.md` |
| Research: Docker subpath | `docs/exploration/docker-subpath-research.md` |
| Research: Flox patterns | `docs/exploration/flox-per-project-research.md` |
| Research: Flox in Docker | `docs/exploration/flox-docker-research.md` |
| Research: Compose portability | `docs/exploration/docker-compose-portability-research.md` |
| Phase 2 spec (superseded) | `docs/specs/container-volume-topology.md` |
| Agent prompts | `.opencode/prompts/` |
| Controller code | `src/agent_framework/controller/` |
| Schema + validators | `src/agent_framework/schema.py`, `validators.py` |
| Type defaults | `src/agent_framework/defaults.json` |
| Learnings: bootstrap (Session 005) | `docs/learnings/bootstrap/2026-05-12-spec.md` |
| Learnings: bootstrap (Session 006) | `docs/learnings/bootstrap/2026-05-12-session-006.md` |
