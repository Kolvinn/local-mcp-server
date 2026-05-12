# Session Handoff — Session 006

**Date:** 2026-05-12
**Handoff to:** Next agent or human continuation
**Primary context files:** This file + `docs/plans/overhaul/MASTER_STATUS.md`

---

## 1. What Happened This Session

### Major Architecture Pivot

The original goal was to implement Part 02 (Schema & Validation) and Part 03 (Bootstrap CLI) from the bootstrap system specs. During implementation, a **fundamental architecture change** was identified and approved by the user:

**OLD:** Static bootstrap script (`bootstrap.py`) runs on host, generates compose file, user runs `docker compose up`
**NEW:** Single controller container holds Docker socket, exposes CLI + MCP, dynamically manages agent lifecycle

This changes the role of "bootstrap" from a one-time host script to a **persistent controller service**.

### What Was Built

**Part 02 — Schema & Validation (COMPLETED)**
- `src/agent_framework/schema.py` — Pydantic models for `agent-project.yaml` and `manifest.json`
- `src/agent_framework/validators.py` — Validation rules, type defaults, manifest generation
- `src/agent_framework/defaults.json` — Agent type registry with default graph modules, prompts, skills
- Removed `governance` from agent type registry (confirmed: governance is a server concept, not an agent type)

**Part 03 — Controller Container (COMPLETED — replaces bootstrap CLI)**
- `src/agent_framework/controller/registry.py` — JSON persistence for project/agent state
- `src/agent_framework/controller/docker_ops.py` — Docker SDK wrapper (volumes, subpaths, manifests, compose execution)
- `src/agent_framework/controller/compose.py` — Dynamic compose file generation, add/remove agent services
- `src/agent_framework/controller/cli.py` — User-facing CLI (`agentctl` commands)
- `src/agent_framework/controller/mcp_server.py` — MCP tools for orchestrator communication
- `src/agent_framework/controller/entrypoint.py` — Container startup script

### Key Design Decisions Made This Session

| Decision | Rationale |
|----------|-----------|
| Controller container replaces bootstrap script | Single container holds Docker socket, no host access needed after initial controller creation |
| Dynamic single compose file | `add-agent` appends to compose, `remove-agent` deletes service + stops container. Simpler than `include:` pattern. |
| 4 volumes per project | `project_vol` (shared data), `agent_vol` (subpaths), `flox_vol` (shared env), `controller_state_vol` (registry) |
| Flox volume mounted RO in agents | User controls env via controller or host, agents get exec but not write |
| MCP + CLI dual interface | User uses CLI via `docker exec`, orchestrator uses MCP tools |
| Registry tracks endpoints | Orchestrator queries `get_agent_endpoint()` to discover agent ACP URLs |
| Governance removed from agent types | Governance is the controller server itself, not an agent that gets provisioned |

---

## 2. Files Created/Modified

| File | Action | Notes |
|------|--------|-------|
| `src/agent_framework/__init__.py` | Created | Package exports |
| `src/agent_framework/schema.py` | Created | Pydantic models for config + manifest |
| `src/agent_framework/validators.py` | Created | Validation, defaults, manifest generation |
| `src/agent_framework/defaults.json` | Created | Type registry (7 types, governance removed) |
| `src/agent_framework/bootstrap.py` | Created | Stub placeholder (superseded by controller) |
| `src/agent_framework/controller/__init__.py` | Created | Controller package exports |
| `src/agent_framework/controller/registry.py` | Created | JSON registry for project/agent state |
| `src/agent_framework/controller/docker_ops.py` | Created | Docker SDK operations |
| `src/agent_framework/controller/compose.py` | Created | Compose file generation |
| `src/agent_framework/controller/cli.py` | Created | `agentctl` CLI |
| `src/agent_framework/controller/mcp_server.py` | Created | MCP server for orchestrator |
| `src/agent_framework/controller/entrypoint.py` | Created | Container startup |
| `src/pyproject.toml` | Modified | Added `docker>=7.1.0` dependency |
| `docs/specs/bootstrap-system-02-schema.md` | Modified | Removed governance from type registry table |

---

## 3. What Is Complete vs What Remains

### ✅ COMPLETE
- [x] Config schema (Pydantic models)
- [x] Config validation (all rules from spec Part 02)
- [x] Type defaults registry
- [x] Manifest generation
- [x] Controller container Python code (CLI + MCP + registry + compose gen)
- [x] Dynamic compose add/remove agent

### ⏳ PENDING — Next Implementation Stages
- [ ] **Controller Dockerfile** — Needs: Docker socket mount, Python 3.14, uv, docker-py, Flox
- [ ] **Agent base image** — User will build (`langgraph-agent-base:latest`). Needs: Flox, uv, Deep Agents, LangGraph, ACP
- [ ] **Entrypoint spec (Part 04)** — `entrypoint.py` for agent containers: read manifest → load graph → MCP tools → `create_deep_agent()` → ACP
- [ ] **Actual Docker testing** — None of the controller code has been tested against a real Docker daemon
- [ ] **ACP container transport** — `deepagents-acp` only documents stdio. Container-to-container ACP needs investigation
- [ ] **Flox integration** — `.flox/` directory structure in `flox_vol`, activation in agent entrypoint
- [ ] **Skills symlink logic** — Deferred during design; may not be needed if skills are injected via Deep Agents `skills=` parameter
- [ ] **Governance reconciliation** — Controller startup recovery from state drift (containers running but not in registry)
- [ ] **Controller self-bootstrap** — How does the first controller container get created? (User will handle manually per discussion)

### 📋 BACKLOG (unchanged)
- GraphRAG (A3-A6)
- Multi-project orchestration
- Agent variations beyond base types
- Symlink bridge for per-file grants

---

## 4. Original Goals vs Current Goals

| Aspect | Original Goal (from Session 005 handoff) | Current Goal (post-pivot) |
|--------|-----------------------------------------|---------------------------|
| **Bootstrap** | `bootstrap.py` CLI runs on host, generates static compose | Controller container manages everything dynamically via Docker socket |
| **Governance** | Separate MCP container spec to be written later | Governance IS the controller container (MCP server + CLI) |
| **Compose** | Static `docker-compose.{project}.yml` | Dynamic single-file compose, rewritten on add/remove |
| **Agent lifecycle** | Static — defined at bootstrap time | Dynamic — orchestrator can provision/destroy via MCP |
| **User interaction** | Run `python bootstrap.py` on host | `docker exec` into controller for CLI |
| **Volumes** | 2 volumes (project + agent) | 4 volumes (+ flox + controller state) |
| **Flox** | Not in initial scope | Shared flox_vol, RO in agents |

---

## 5. Critical Context for Next Agent

### Architecture Must-Knows

1. **Controller is the governance layer** — There is no separate "governance container." The controller container IS the governance MCP server.

2. **No host access after controller creation** — The user creates the controller container manually (they said "I'll create the default container"). After that, everything happens inside containers.

3. **Agent types** — 6 valid types: `orchestrator`, `system_thinker`, `implementer`, `auditor`, `explorer`, `memory_manager`. Governance is NOT an agent type.

4. **Compose generation** — The controller generates a single compose file per project. When adding an agent, it appends the service and runs `docker compose up -d {agent}`. When removing, it stops the service, removes it from the compose file.

5. **Subpaths must pre-exist** — Docker requires subpath directories to exist in the volume before containers with `subpath:` mounts can start. The controller creates these via alpine init containers.

### Code Structure

```
src/agent_framework/
├── __init__.py          # Package exports
├── schema.py            # Pydantic models (config + manifest)
├── validators.py        # Validation + defaults + manifest generation
├── defaults.json        # Type registry
├── bootstrap.py         # Stub (superseded)
└── controller/
    ├── __init__.py      # Controller exports
    ├── registry.py      # JSON persistence
    ├── docker_ops.py    # Docker SDK wrapper
    ├── compose.py       # Compose file generation
    ├── cli.py           # User CLI (agentctl)
    ├── mcp_server.py    # MCP tools for orchestrator
    └── entrypoint.py    # Container startup
```

### Important Files to Read

1. `docs/plans/overhaul/MASTER_STATUS.md` — Master context
2. `docs/specs/bootstrap-system-02-schema.md` — Config schema (updated, governance removed)
3. `docs/specs/bootstrap-system-03-bootstrap.md` — Original bootstrap spec (largely superseded, but validation rules still relevant)
4. `docs/specs/bootstrap-system-04-entrypoint.md` — Next major piece to implement
5. `src/agent_framework/defaults.json` — Current type defaults

---

## 6. Next Steps (Prioritized)

### Immediate (next session)
1. **Review controller code** — Verify it matches the approved design. Test imports. Look for TODOs.
2. **Controller Dockerfile** — Create Dockerfile for controller container. Needs: Python 3.14, uv, docker-py, FastMCP, Flox.
3. **Agent entrypoint (Part 04)** — `entrypoint.py` that runs inside agent containers: reads manifest → loads graph → MCP tools → `create_deep_agent()` → ACP exposure.

### Short-term
4. **End-to-end test** — Bootstrap a project via controller, verify containers start, verify registry state.
5. **ACP transport investigation** — How does orchestrator connect to agent ACP endpoints? `deepagents-acp` stdio vs HTTP/SSE.

### Medium-term
6. **Flox environment setup** — Default Flox manifest for agents, activation in entrypoint.
7. **Controller state reconciliation** — On startup, verify running containers match registry.
8. **Skills loading** — Decide if skills are symlinks, volume mounts, or Deep Agents `skills=` parameter.

---

## 7. Known Issues / Technical Debt

1. **Untested Docker code** — `docker_ops.py` has not been run against a real Docker daemon. The `compose_down` per-service logic uses `docker compose stop + rm` which may leave networks/volumes dangling.

2. **Compose YAML header** — The compose file uses a simple text header. If `yaml.dump` produces invalid YAML, the header won't be parsed correctly. Should use proper YAML comments.

3. **Agent base image hardcoded** — `langgraph-agent-base:latest` is assumed. The controller does not validate image existence.

4. **MCP transport** — Currently SSE on port 8000. If multiple controllers run (one per project), port conflicts need management.

5. **No auth** — MCP server is unauthenticated. Acceptable for single-user MVP but needs review.

6. **Graph module validation** — `validate_graph_module()` in validators.py does `importlib.import_module()` which requires the graph module to be importable in the host environment. This is only validated if `validate_graphs=True`.

7. **Model regex** — Updated to allow hyphens in provider name (`opencode-go:...`). May need further adjustment for other provider formats.

---

## 8. Rules for Next Agent

Same as MASTER_STATUS.md §0:
1. No autonomous decisions — pause and ask user
2. User is most efficient data source
3. Wide and tentative — surface options
4. Don't assume intent
5. Don't over-summarize
6. Goal refinement only unless ordered
7. No host access — agents never touch host filesystem
8. User is Governor
9. Context Economy — be concise
10. Learnings Recording — write to `docs/learnings/{domain}/{session}.md`

---

## 9. Design Artifacts from This Session

The following design was approved by the user during this session and implemented:

### Volume Topology (4 volumes per project)

```
{project}_project_vol    → /app/project    (agents: RO, orchestrator: RW)
{project}_agent_vol      → /workspace      (agents: subpath per agent)
{project}_flox_vol       → /flox           (agents: RO+exec, controller: RW)
controller_state_vol     → /state          (controller only, persistent)
```

### Controller Container

- Image: `ghcr.io/{user}/agent-controller:latest` (user builds)
- Mounts: Docker socket, `{project}_agent_vol`, `{project}_flox_vol`, `controller_state_vol`
- Ports: MCP SSE (default 8000)
- Entry: `python -m agent_framework.controller.entrypoint`

### CLI Commands

```bash
# Inside controller container
docker exec -it controller agentctl validate /config/agent-project.yaml
docker exec -it controller agentctl bootstrap /config/agent-project.yaml
docker exec -it controller agentctl add-agent /config/agent-project.yaml <agent_key>
docker exec -it controller agentctl remove-agent <project> <agent_key>
docker exec -it controller agentctl list-agents <project>
docker exec -it controller agentctl teardown /config/agent-project.yaml
docker exec -it controller agentctl show-registry
```

### MCP Tools

- `validate_project` — Validate config
- `bootstrap_project` — Full bootstrap
- `provision_agent` — Add agent to running stack
- `destroy_agent` — Remove agent
- `list_agents` — Return agent list
- `get_agent_endpoint` — Return ACP URL
- `get_agent_status` — Check container status

---

(End of handoff)
