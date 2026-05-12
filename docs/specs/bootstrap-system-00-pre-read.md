---
title: Bootstrap System — Implementer Pre-Read
version: 1.0
date_created: 2026-05-12
purpose: Tells Implementer which skills to load and context to read before coding each spec.
---

# Implementer Context & Skill Injection

Each spec part requires different domain knowledge. Load the listed skills
and read the listed context files BEFORE writing code for that part.

---

## Part 01 — Overview (no code)

Read-only. Understand the system before starting.

**Context files:**
- `docs/plans/overhaul/MASTER_STATUS.md`
- `docs/plans/overhaul/SESSION_HANDOFF.md`
- `docs/plans/overhaul/bootstrap_project.sh` (what's being replaced)

**Skills:** None (no code to write)

---

## Part 02 — Schema & Validation (`agent-project.yaml`)

Implement: YAML loading, schema validation, manifest generation, type defaults.

**Skills to load:**
| Skill | Why |
|-------|-----|
| `pydantic` | Validation models for config schema |
| `python-type-safety` | Type annotations for validation functions |
| `python-expert` | General code quality |

**Context files:**
- `docs/specs/bootstrap-system-02-schema.md` (the spec itself)
- `docs/specs/bootstrap-system-01-overview.md` (architecture context)
- `.opencode/opencode.jsonc` (reference: similar agent config structure)
- `docs/plans/overhaul/agent-variation-matrix.md` (type registry defaults)

**Domain knowledge needed:**
- YAML frontmatter validation (SKILL.md format from `deep-agents-core` skill)
- Docker volume naming constraints (lowercase, alphanumeric, hyphens, 1-63 chars)
- Docker container naming constraints (no hyphens in subpath keys)
- `importlib.import_module()` for graph module validation

---

## Part 03 — Bootstrap CLI (`bootstrap.py`)

Implement: Docker volume creation, subdirectory seeding, symlink creation,
manifest writing, compose generation. Uses `docker-py` SDK.

**Skills to load:**
| Skill | Why |
|-------|-----|
| `python-best-practices` | CLI structure, error handling |
| `python-type-safety` | Type annotations |
| `context7` | Look up `docker-py` SDK API (volume create, container run) |
| `pydantic` | If reusing validation models from Part 02 |

**Context files:**
- `docs/specs/bootstrap-system-03-bootstrap.md` (the spec itself)
- `docs/specs/bootstrap-system-02-schema.md` (validation rules to call)
- `docs/specs/bootstrap-system-05-skills.md` (symlink model)
- `docs/exploration/docker-subpath-research.md` (subpaths must pre-exist)
- `docs/exploration/docker-compose-portability-research.md` (compose generation)

**Domain knowledge needed:**
- `docker.from_env()` — Docker SDK entry point
- `client.volumes.create(name=..., driver="local")` — volume creation
- `client.containers.run(image="alpine:latest", command=[...], volumes={...}, remove=True)` — init containers
- Docker compose YAML structure (services, volumes, networks, `volume: subpath:`)
- Relative symlink resolution across two mounted volumes
- Alpine shell: `mkdir -p`, `ln -sfn`, heredoc for writing manifest.json

**External docs to consult:**
- `docker-py` readthedocs: `https://docker-py.readthedocs.io/en/stable/`

---

## Part 04 — Agent Container Entrypoint (`entrypoint.py`)

Implement: Manifest reading, graph loading, MCP tool loading, agent creation,
ACP exposure. This is the most framework-heavy part.

**Skills to load:**
| Skill | Why |
|-------|-----|
| `deep-agents-core` | `create_deep_agent()` parameters, skills, backends, middleware |
| `deep-agents-orchestration` | `interrupt_on`, subagents, HITL patterns |
| `deep-agents-memory` | `FilesystemBackend`, `StoreBackend`, checkpointer setup |
| `langgraph-fundamentals` | `StateGraph`, `CompiledStateGraph`, `get_graph()` contract |
| `langgraph-persistence` | `MemorySaver`, `InMemoryStore`, thread_id patterns |
| `langchain-fundamentals` | `@tool` decorator, tool loading, agent creation |
| `langchain-middleware` | `HumanInTheLoopMiddleware`, `interrupt_on`, HITL resume |
| `async-python-patterns` | `asyncio.run()`, async MCP client, async agent invoke |
| `python-type-safety` | Type annotations for async functions |
| `python-best-practices` | Error handling, logging, env var management |

**Context files:**
- `docs/specs/bootstrap-system-04-entrypoint.md` (the spec itself)
- `docs/specs/bootstrap-system-02-schema.md` (manifest schema)
- `docs/specs/bootstrap-system-05-skills.md` (MCP loading model)
- `docs/plans/overhaul/MASTER_STATUS.md` (constraints: Python 3.14+, env vars only)

**Domain knowledge needed:**
- `from deepagents import create_deep_agent` — all parameters per customization page
- `from deepagents_acp.server import AgentServerACP` — wraps agent for ACP
- `from acp import run_agent` — starts ACP server (stdio mode)
- `from langchain_mcp_adapters.client import MultiServerMCPClient` — MCP tool loading
- `client.get_tools()` is async — must be `await`ed
- MCP endpoint config: `{name: {transport, url}}` or `{name: {transport, command, args}}`
- `FilesystemBackend(root_dir=..., virtual_mode=True)` for Deep Agents
- `MemorySaver()` and `InMemoryStore()` for MVP (PostgresSaver/PostgresStore later)
- Graph module contract: must expose `get_graph() -> CompiledStateGraph`, optionally `get_tools() -> list`

**External docs to consult:**
- Deep Agents customization: `https://docs.langchain.com/oss/python/deepagents/customization.md`
- LangChain MCP: `https://docs.langchain.com/oss/python/langchain/mcp.md`
- Deep Agents ACP: `https://docs.langchain.com/oss/python/deepagents/acp.md`

---

## Part 05 — Skills & MCP (symlink logic, no standalone code)

Most logic is implemented in Part 03 (bootstrap). This spec is primarily
architectural documentation with some validation code shared with Part 02.

**Skills to load:**
| Skill | Why |
|-------|-----|
| `python-best-practices` | SKILL.md validation function |
| `python-type-safety` | Type annotations |

**Context files:**
- `docs/specs/bootstrap-system-05-skills.md` (the spec itself)
- `docs/plans/overhaul/MASTER_STATUS.md` §8 (MCP endpoint access delegation)

**Domain knowledge needed:**
- YAML frontmatter parsing (same as Part 02 skill validation)
- Symlink creation via alpine init container (shared with Part 03)
- Two-volume mount resolution (relative symlink `../../shared/skills/{name}` resolves at container runtime)

---

## Cross-Cutting Concerns (All Parts)

**Project constraints (from MASTER_STATUS.md):**
- Python 3.14+
- `uv` package manager
- No `npx` — `bunx` only
- No hardcoded secrets — env vars only
- `src/` is NOT a Python package
- Flox replaces conda
- Specs/docs ≤ 350 lines (this pre-read is intentionally short)

**Session rules (from SESSION_HANDOFF.md):**
- No autonomous decisions — pause and ask before acting
- User is most efficient data source
- Wide and tentative
- Don't assume intent
- Goal refinement only unless ordered to design/build

---

## Suggested Implementation Order

1. **Part 02** (schema/validation) — foundation; Part 03 depends on it
2. **Part 03** (bootstrap CLI) — uses validation from Part 02; produces volumes and manifests
3. **Part 04** (entrypoint) — consumes manifests from Part 03; can be developed in parallel after Part 02 is done
4. **Part 05** — validation functions shared with Part 02; symlink logic shared with Part 03
