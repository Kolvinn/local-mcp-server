---
title: Bootstrap System — Overview & Architecture
version: 1.0
date_created: 2026-05-12
owner: User (direct session)
tags: [infrastructure, architecture, bootstrap, docker]
---

# Introduction

The bootstrap system translates a declarative `agent-project.yaml` config into a running
Docker-based agentic stack. It replaces the current `bootstrap_project.sh` bash script
with a Python CLI that uses the Docker SDK, and specifies the per-agent container
entrypoint that wires LangGraph graphs, MCP tools, Deep Agents skills, and ACP exposure.

## 1. Purpose & Scope

### Purpose
Given a project config enumerating agents (name, type, model, skills, MCP endpoints,
graph module), produce:

1. Two external Docker volumes (`{project}_project_vol`, `{project}_agent_vol`)
2. Pre-created subdirectories inside `agent_vol` (required by Docker for `subpath:` mounts)
3. A skeleton on `project_vol` (`shared/skills/`, `shared/knowledge/`, `shared/config/`)
4. A `docker-compose.{project}.yml` with correct volume mounts, networks, and per-agent container definitions
5. A per-agent `manifest.json` in each subpath, derived from the config, that the container entrypoint reads at startup

### Out of Scope (this spec)
- Interactive walkthrough / TUI (backlog)
- Multi-project orchestration (backlog)
- Governance container implementation (separate spec)
- ACP transport mode selection for containers (currently stdio-only per Deep Agents ACP docs; container transport TBD)
- Tool function definitions (deferred)

### Intended Audience
Implementer translating this spec into `bootstrap.py` and container entrypoint scripts.

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Bootstrap** | One-time infrastructure setup: volumes, subdirectories, compose file, manifests |
| **Entrypoint** | Script that runs inside each container at startup, wiring the agent |
| **ACP** | Agent Client Protocol — stdio-based protocol for editor-agent integration |
| **MCP** | Model Context Protocol — tool provisioning from external servers |
| **`MultiServerMCPClient`** | `langchain-mcp-adapters` client that loads tools from MCP server URLs |
| **`create_deep_agent`** | Deep Agents factory function producing a `CompiledStateGraph` |
| **`AgentServerACP`** | `deepagents-acp` wrapper exposing a deep agent over ACP |
| **Subpath** | Docker `volume:` mount option isolating a subdirectory per container |
| **Manifest** | Per-agent JSON file in the agent's subpath driving entrypoint behavior |

## 3. System Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVELOPER HOST                                                  │
│                                                                  │
│  $ python bootstrap.py bootstrap agent-project.yaml              │
│         │                                                        │
│         ├── 1. Validate YAML schema                              │
│         ├── 2. Create external Docker volumes (if missing)       │
│         ├── 3. Pre-create subdirectories in agent_vol            │
│         ├── 4. Seed project_vol skeleton                         │
│         ├── 5. Symlink allowed skills per agent                  │
│         ├── 6. Write per-agent manifest.json                     │
│         └── 7. Generate docker-compose.{project}.yml             │
│                                                                  │
│  $ docker compose -f docker-compose.{project}.yml up -d          │
│         │                                                        │
│         ├── governance (if configured, future)                   │
│         ├── orchestrator container                               │
│         │     └── entrypoint: reads manifest.json               │
│         │         → loads graph module                           │
│         │         → loads MCP tools via MultiServerMCPClient     │
│         │         → create_deep_agent(...)                       │
│         │         → AgentServerACP(agent).run()                  │
│         ├── agent container                                      │
│         │     └── (same entrypoint pattern)                      │
│         └── ...                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Bootstrap vs Runtime
- **Bootstrap** (bootstrap.py) runs ONCE on the host. Creates volumes, skeletons, manifests, compose.
- **Runtime** (container entrypoint) runs EVERY container start. Reads manifest, wires agent, exposes ACP.
- **Skills** are symlinked at bootstrap time from `shared/skills/` → agent subpath `skills/`. Runtime doesn't modify symlinks.
- **MCP tools** are loaded at runtime (entrypoint) from endpoints defined in manifest. Governance proxies these during build phase.

## 4. File Map

| File | Phase | Machine | Purpose |
|------|-------|---------|---------|
| `agent-project.yaml` | Input | Host | Declarative project config |
| `bootstrap.py` | Bootstrap | Host | Python CLI, Docker SDK |
| `docker-compose.{project}.yml` | Output | Host | Generated compose file |
| `manifest.json` (per agent) | Output | agent_vol subpath | Drives container entrypoint |
| `entrypoint.py` | Runtime | Container | Agent wiring + ACP exposure |
| `shared/skills/{name}/SKILL.md` | User-managed | project_vol | Skill definitions |

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Config drives everything | Single source of truth. No hardcoded agent lists in bootstrap or entrypoint. |
| Manifest as intermediate artifact | Bootstrap writes JSON; entrypoint reads JSON. Decouples bootstrap from runtime. |
| Flat agent map (not type registry + instances) | Simpler. Variations not yet built. Regroup when variations exist. |
| `interrupt_on` in config from start | Low complexity (dict passthrough). Avoids config migration later. |
| Skills symlinked at bootstrap, not runtime | Docker volumes are immutable to agents (RO on project_vol). Symlinks must be created by bootstrap on host. |
| Governance not in initial compose | Governance spec not yet written. Bootstrap generates orchestrator + agents only for MVP. |

## 6. Reference Map

| What | Where |
|------|-------|
| Architecture overview | `docs/plans/overhaul/MASTER_STATUS.md` |
| Session handoff | `docs/plans/overhaul/SESSION_HANDOFF.md` |
| Current bash bootstrap | `docs/plans/overhaul/bootstrap_project.sh` |
| Agent variation matrix | `docs/plans/overhaul/agent-variation-matrix.md` |
| Docker architecture chat | `docs/plans/overhaul/docker_architecture_chat.md` |
| Schema spec | `docs/specs/bootstrap-system-02-schema.md` |
| Bootstrap CLI spec | `docs/specs/bootstrap-system-03-bootstrap.md` |
| Entrypoint spec | `docs/specs/bootstrap-system-04-entrypoint.md` |
| Skills & MCP spec | `docs/specs/bootstrap-system-05-skills.md` |
