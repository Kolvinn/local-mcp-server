# Session Handoff — Session 004

**Date:** 2026-05-12
**Handoff to:** Next agent or human continuation
**Primary context files:** `docs/plans/overhaul/MASTER_STATUS.md` + this file

---

## 1. What Happened This Session

### Architecture solidified
- **Every agent is a Docker container.** No OpenCode subagents. OpenCode phased out eventually.
- **Governance MCP container** is the central server — sole Docker socket holder, agent lifecycle manager, MCP proxy for all agent-to-external communication. Transitions from proxy to router once agents have their own MCP servers.
- **Two external named volumes per project** (not one master volume):
  - `{project}_project_vol` — shared RO for agents, RW for orchestrator. Contains `shared/skills/`, `shared/knowledge/`, `shared/config/`.
  - `{project}_agent_vol` — per-agent RW isolation via Docker `volume: subpath:` option. Subdirectories (orchestrator, agent1, agent2, memory_manager, etc.) pre-created at bootstrap.
- **One agentic stack per project.** Two projects = two independent docker-compose stacks, two volume pairs, two governance containers. Fully isolated.
- **The agentic framework is a standalone product** in its own git repo. Projects are external data it consumes. Agentic memory/learnings never touch the project repo.
- **Dual-protocol model**: MCP over SSE (control plane: governance ↔ orchestrator) and ACP via `acp-sdk-python` (runtime: orchestrator ↔ agents, user/TUI ↔ agents). ACP not yet built.
- **Skills served from project volume**: User installs skills per project via `bunx skills add` on the project volume. Orchestrator symlinks allowed skills into agent subpaths based on allowlist. Agents have a `read_skill` tool that reads from their local skills directory.
- **Flox baked into Docker image**, not on volumes. PATH bypass (`.flox/run/bin` on PATH) for zero activation overhead. Per-agent customization via `[include]` composition if needed later.
- **`uv` treated as user territory** — confirmed NOT in Flox catalog by explorer, but user states it is. Use `ghcr.io/astral-sh/uv` base image pattern from prior specs.

### MCP Registration & Access Delegation designed
- Governance is sole MCP proxy during build phase. Agents route all MCP requests through governance.
- Per-agent endpoint allowlist in `manifest.json` (`mcp_endpoints.allowed`).
- Eventual migration: proxy → router (agents get their own MCP servers, governance becomes registry).
- See MASTER_STATUS.md §8 for full detail.

### Bootstrap script written
- `docs/plans/overhaul/bootstrap_project.sh` — creates volumes, pre-creates subdirectories, seeds project skeleton, generates `docker-compose.{project}.yml`.
- Validated: YAML parses correctly. Targets absolute. Volume mounts correct (RO for agents on project_vol, RW for orchestrator on project_vol; subpath-based RW on agent_vol for all).

### Three research tasks completed
- `docs/exploration/docker-subpath-research.md` — subpaths must pre-exist, `external: true` + subpath is compatible, same-volume dual-mount is undefined behavior (we avoid this by using two separate volumes).
- `docs/exploration/flox-per-project-research.md` — `flox activate -d /volume/path` works, Nix store can't live on volume, `[include]` composition viable for per-agent customization, bun + nodejs confirmed in Flox catalog.
- `docs/exploration/docker-compose-portability-research.md` — project name isolation is automatic, variable substitution with per-project `.env` files recommended, omit `external: true` for auto-prefixed volumes.

---

## 2. Key Decisions

| Decision | Rationale |
|----------|-----------|
| Two volumes per project (not one) | Docker subpath on same volume mounted twice in one container is undefined. Separate volumes (project_vol + agent_vol) avoids mount overlap. |
| Governance MCP is permanent central server | Starts as proxy, transitions to router. Also serves skills and manages agent lifecycle. Never removed. |
| Bootstrap script controls initial layout | User runs it on host. Creates volumes, pre-creates subdirectories (required per Docker docs), generates compose. Inner spawning via governance comes after bootstrap. |
| Per-project isolation (not global) | Each project gets its own compose stack, volumes, governance. No shared global infrastructure. |
| Skills on project volume, symlinked per agent | Orchestrator manages allowlist → symlinks from `shared/skills/` into agent subpaths. Agent tool `read_skill` reads local skills dir. |
| Scope narrowed: bootstrap only, not multi-project | Get single-project spawning working first. Multi-project templates come later. |
| Subpaths assumed to work despite explorer findings | User will debug. Two-volume approach avoids the undefined dual-mount pattern anyway. |

---

## 3. Files Created/Modified This Session

| File | Action |
|------|--------|
| `docs/plans/overhaul/MASTER_STATUS.md` | Created, updated throughout session — single source of truth |
| `docs/plans/overhaul/SESSION_HANDOFF.md` | This file — rewrites Session 003 handoff |
| `docs/plans/overhaul/bootstrap_project.sh` | Created — bootstrap script for project infrastructure |
| `docs/exploration/docker-subpath-research.md` | Created — Docker subpath behavior research |
| `docs/exploration/flox-per-project-research.md` | Created — Flox per-project patterns (extends prior research) |
| `docs/exploration/docker-compose-portability-research.md` | Created — multi-instance compose portability |
| `docs/plans/overhaul/test_compose.md` | Pre-existing — user's compose attempt (reference only, has issues) |

---

## 4. Component Status Summary

| Component | Status |
|-----------|--------|
| Memory Manager (`src/memory/`) | Built, not tested, no endpoint (needs ACP wrapper) |
| RAG Pipeline A1+A2 | Built, functional, 82 tests pass. Missing GraphRAG (A3-A6) |
| Governance MCP Container | Spec only (from docker_architecture_chat.md) |
| Agent Container Template (`langgraph-agent-base`) | Spec only — needs Dockerfile design |
| Orchestrator Container | Spec only |
| Bootstrap Script | Written, YAML validated, untested (needs Docker to test) |
| ACP Protocol | Not designed, not built |
| FastMCP Memory Server | Built, may be superseded by Memory Manager |
| Agent Prompts (`.opencode/prompts/`) | Active but will migrate to container-injected context |

---

## 5. Current Phase

- Phase 0: Planning — ✅
- Phase 1: Agent Design — ✅
- Phase 2: Container & Volume Topology — ✅ (this session: solidified, bootstrap script written)
- **Phase 3: LangGraph State Management — pending**
- Phase 4-8: pending

Phase 2 deliverables for next agent:
1. Agent Dockerfile template (`langgraph-agent-base` image)
2. Governance MCP server pseudocode spec
3. Updated docker-compose with governance + orchestrator + agents (beyond the bootstrap skeleton)

---

## 6. Exact Next Steps (in order)

1. **Design agent Dockerfile template** — single image for all agent types. Flox for system tools (bun, ripgrep, jq, git, python). uv for Python packages (langchain, langgraph, pydantic, etc.). PATH bypass (`.flox/run/bin`). Base image: `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` + Flox apt install.
2. **Design governance MCP server spec** — FastMCP + Docker SDK. Tools: `provision_agent`, `destroy_agent`, `list_agents`, `modify_agent_capability`. SSE transport. State persistence to governance_state volume. Agent name validation (regex). Subpath pre-creation in `provision_agent`.
3. **Update docker-compose** — add governance container (with docker.sock mount), add internal network, parameterize project name.
4. **Test bootstrap script** — user must test with Docker. Key risks: subpath pre-creation, volume mount ordering, compose up.
5. **Wire Memory Manager with ACP endpoint** — once ACP is designed and agent template exists.
6. **Backlog items**: symlink bridge, multi-project templates, agent variations, researcher/tester agents, GraphRAG.

---

## 7. Rules the Next Agent Must Follow

From the governing session context (`essential_context.md` rules, adapted):

1. **No autonomous decisions** — pause and ask user before acting
2. **User is most efficient data source** — ask before delegating to Explorer, loading skills, writing files
3. **Wide and tentative** — surface options/trade-offs, don't commit without user gate
4. **Don't assume intent** — ambiguity → query user directly
5. **Don't over-summarize** what user tells you to read — waste of tokens
6. **Goal refinement only** unless ordered to design/build

Additional project rules:

7. **No host access** — agents never access host filesystem, only Docker volumes
8. **User is Governor** — permissions bubble up, never assumed downward
9. **Context Economy** — be concise, point to files, save context window
10. **Learnings Recording** — after completing work, record to `docs/learnings/{domain}/{session}.md`

---

## 8. What to Read First

1. **`docs/plans/overhaul/MASTER_STATUS.md`** — definitive context (component statuses, architecture, protocols, constraints, volume topology, reference map)
2. **This file** — what happened, what's next
3. **`docs/plans/overhaul/docker_architecture_chat.md`** — full design chat (governance spec, agent template, manifest system)
4. **`docs/plans/overhaul/bootstrap_project.sh`** — bootstrap script (see what generate compose looks like)
5. **`docs/exploration/docker-subpath-research.md`** — subpath pre-creation requirement is critical
6. **`docs/exploration/flox-per-project-research.md`** §9 — recommended Dockerfile pattern
