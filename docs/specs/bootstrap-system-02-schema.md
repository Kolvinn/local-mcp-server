---
title: Bootstrap System — agent-project.yaml Schema
version: 1.0
date_created: 2026-05-12
owner: User (direct session)
tags: [schema, config, yaml, validation]
---

# Introduction

`agent-project.yaml` is the single declarative config driving the entire bootstrap
pipeline. It enumerates agents with their type, model, skills, MCP endpoints,
graph module, and HITL policies. Bootstrap reads it to generate volumes, compose,
and per-agent manifests. The container entrypoint reads the manifest to wire the agent.

## 1. Purpose & Scope

Define the exact YAML schema, field-by-field constraints, validation rules,
and type-to-defaults mapping. The schema is intentionally flat (no type registry +
instances pattern) because per-agent variations aren't yet built.

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Agent key** | Top-level YAML key under `agents:` — becomes container_name and volume subpath |
| **Agent type** | Maps to a default prompt, default skills, and (optionally) a compiled LangGraph graph |
| **Graph module** | Python dotted path to a module with `get_graph() -> CompiledStateGraph` |
| **MCP endpoint** | URL of an MCP server whose tools are loaded at agent startup |
| **Skill** | Named directory in `shared/skills/` containing a `SKILL.md` file |

## 3. Full Schema

```yaml
# agent-project.yaml

project_name: string                    # REQUIRED. Matches Docker volume naming.

agents:                                 # REQUIRED. Map of agent_key → agent_def.
  <agent_key>:                          # string. Becomes container_name + volume subpath.
    type: string                        # REQUIRED. One of the registered agent types.
    model: string                       # REQUIRED. provider:model-name format.
    system_prompt: string               # OPTIONAL. Inline prompt text.
    system_prompt_file: string          # OPTIONAL. Path to prompt file (relative to repo root).
    graph_module: string                # OPTIONAL. Python dotted path (e.g. agents.memory_manager.graph).
    skills:                             # OPTIONAL. List of skill names to symlink.
      - string
    mcp_endpoints:                      # OPTIONAL. List of MCP servers to load tools from.
      - name: string                    # REQUIRED. Unique identifier for this endpoint.
        transport: string               # REQUIRED. "http" or "stdio".
        url: string                     # REQUIRED if transport=http. MCP server URL.
        command: string                 # REQUIRED if transport=stdio. Executable path.
        args:                           # OPTIONAL. Arguments for stdio command.
          - string
        headers:                        # OPTIONAL. HTTP headers for authentication.
          key: value
    interrupt_on:                       # OPTIONAL. HITL policies per tool.
      <tool_name>:                      # Key = tool name.
        true                            # All decisions allowed.
        # OR:
        allowed_decisions:              # Restricted decision set.
          - approve
          - reject
          - edit
    permissions:                        # OPTIONAL. Filesystem permissions.
      - path: string                    # REQUIRED. Filesystem path pattern.
        read: boolean                   # Default true.
        write: boolean                  # Default false.
```

### Field Constraints

| Field | Type | Required | Default | Constraint |
|-------|------|----------|---------|------------|
| `project_name` | string | YES | — | `^[a-z][a-z0-9_-]{1,63}$` (Docker volume naming) |
| `agents.<key>` | string | YES | — | `^[a-z][a-z0-9_]{1,30}$` (Docker container + subpath naming) |
| `agents.<key>.type` | string | YES | — | Must be a registered type (see §4) |
| `agents.<key>.model` | string | YES | — | `^[a-z_]+:[a-zA-Z0-9_.-]+$` |
| `agents.<key>.system_prompt` | string | NO | type default | Mutually exclusive with `system_prompt_file` |
| `agents.<key>.system_prompt_file` | string | NO | type default | Path must exist at bootstrap time |
| `agents.<key>.graph_module` | string | NO | type default | Must be importable; must expose `get_graph()` |
| `agents.<key>.skills` | list[string] | NO | type default | Each name must have a `shared/skills/{name}/SKILL.md` |
| `agents.<key>.mcp_endpoints[].name` | string | YES (if endpoint) | — | `^[a-z][a-z0-9_]{1,30}$` |
| `agents.<key>.mcp_endpoints[].transport` | string | YES (if endpoint) | — | One of: `"http"`, `"stdio"` |
| `agents.<key>.mcp_endpoints[].url` | string | http: YES, stdio: NO | — | Valid HTTP URL |
| `agents.<key>.mcp_endpoints[].command` | string | stdio: YES, http: NO | — | Executable path (validated for existence if local) |
| `agents.<key>.interrupt_on.<tool>` | bool or object | NO | no interrupts | `true` = all decisions; object = `allowed_decisions` list |
| `agents.<key>.permissions[].path` | string | YES (if permissions) | — | Filesystem path pattern |

### Validation Rules

```
RULE: validate_project_name
INPUT: project_name (string)
OUTPUT: ok or error

BEGIN
    IF project_name DOES NOT MATCH /^[a-z][a-z0-9_-]{1,63}$/ THEN
        RETURN error("project_name must be lowercase alphanumeric with hyphens/underscores, 1-63 chars")
    END IF
    RETURN ok
END

RULE: validate_agent_key
INPUT: key (string)
OUTPUT: ok or error

BEGIN
    IF key DOES NOT MATCH /^[a-z][a-z0-9_]{1,30}$/ THEN
        RETURN error("agent key '{key}' must be lowercase alphanumeric with underscores, 1-30 chars")
    END IF
    IF key CONTAINS "-" THEN
        RETURN error("agent key '{key}' must not contain hyphens (use underscores)")
    END IF
    RETURN ok
END

RULE: validate_type
INPUT: agent_type (string), registered_types (set)
OUTPUT: ok or error

BEGIN
    registered ← {"orchestrator", "system_thinker", "implementer", "auditor", "explorer", "memory_manager", "governance"}
    IF agent_type NOT IN registered THEN
        RETURN error("agent type '{agent_type}' is not registered. Known types: {registered}")
    END IF
    RETURN ok
END

RULE: validate_skills
INPUT: skills (list[string]), project_skills_dir (path)
OUTPUT: ok or error

BEGIN
    FOR EACH skill IN skills DO
        skill_path ← project_skills_dir / skill / "SKILL.md"
        IF NOT file_exists(skill_path) THEN
            RETURN error("skill '{skill}' not found at {skill_path}")
        END IF
        -- Validate SKILL.md has YAML frontmatter with 'name' and 'description'
        content ← read_file(skill_path)
        IF NOT has_frontmatter(content) THEN
            RETURN error("skill '{skill}' SKILL.md missing YAML frontmatter")
        END IF
    END FOR
    RETURN ok
END

RULE: validate_graph_module
INPUT: graph_module (string | None)
OUTPUT: ok or error

BEGIN
    IF graph_module IS None THEN
        RETURN ok  -- optional field
    END IF
    TRY
        module ← importlib.import_module(graph_module)
        IF NOT hasattr(module, "get_graph") THEN
            RETURN error("graph_module '{graph_module}' must expose get_graph()")
        END IF
        graph ← module.get_graph()
        IF NOT isinstance(graph, CompiledStateGraph) THEN
            RETURN error("get_graph() in '{graph_module}' must return CompiledStateGraph")
        END IF
    CATCH ImportError
        RETURN error("graph_module '{graph_module}' cannot be imported")
    CATCH Exception AS exc
        RETURN error("graph_module '{graph_module}' validation failed: {exc}")
    END TRY
    RETURN ok
END
```

## 4. Agent Type Registry

| Type | Default Graph | Default Prompt | Default Skills | Notes |
|------|--------------|----------------|----------------|-------|
| `orchestrator` | `agents/orchestrator/graph.py` | Orchestrator — sole user contact, delegation, approval gates | `planning-with-files` | Primary agent |
| `system_thinker` | `agents/system_thinker/graph.py` | Domain design specialist, wide-before-deep | `sequential-thinking` | No code, no user contact |
| `implementer` | `agents/implementer/graph.py` | Code translator from approved specs | `python-expert` | Reads specs, never briefs |
| `auditor` | `agents/auditor/graph.py` | 5-check verification framework | `python-code-review` | Reads specs+code, never briefs |
| `explorer` | `agents/explorer/graph.py` | Read-only codebase scout | (none) | Returns complete/error only |
| `memory_manager` | `agents/memory_manager/graph.py` | Memory ingestion pipeline | `langchain-rag`, `qdrant-vector-search` | Has compiled graph |


Defaults are applied at bootstrap time during manifest generation. If the agent config
overrides a field, the override wins. If neither config nor type default provides a value
for a REQUIRED field (like `model`), validation fails.

## 5. Manifest Generation

For each agent, bootstrap writes `{agent_vol_subpath}/manifest.json`:

```json
{
    "agent_key": "memory_manager",
    "type": "memory_manager",
    "model": "openai:gpt-4.1",
    "system_prompt": "You are a memory ingestion specialist...",
    "graph_module": "agents.memory_manager.graph",
    "skills": ["langchain-rag", "qdrant-vector-search"],
    "mcp_endpoints": [
        {
            "name": "qdrant",
            "transport": "http",
            "url": "http://qdrant:6333"
        }
    ],
    "interrupt_on": {},
    "permissions": [],
    "workspace_path": "/workspace",
    "project_path": "/app/project",
    "skills_path": "/workspace/skills"
}
```

Manifest is JSON (not YAML) because the container entrypoint reads it with `json.load()`
— no YAML parser dependency needed inside the container.

## 6. Example Config

```yaml
project_name: demo

agents:
  orchestrator:
    type: orchestrator
    model: opencode-go/deepseek-v4-pro
    system_prompt: |
      You are the project orchestrator. Delegate tasks, never execute them directly.
    skills:
      - planning-with-files
    mcp_endpoints:
      - name: governance
        transport: http
        url: http://governance:8000/mcp

  memory_manager:
    type: memory_manager
    model: openai:gpt-4.1
    graph_module: agents.memory_manager.graph
    skills:
      - langchain-rag
      - qdrant-vector-search
    mcp_endpoints:
      - name: qdrant
        transport: http
        url: http://qdrant:6333
      - name: lite_llm
        transport: http
        url: http://lite_llm:4000
    interrupt_on:
      delete_memory: true

  implementer:
    type: implementer
    model: opencode-go/deepseek-v4-flash
    skills:
      - python-expert
      - pydantic
      - python-type-safety
    permissions:
      - path: /workspace/*
        read: true
        write: true
      - path: /app/project/*
        read: true
        write: false

  auditor:
    type: auditor
    model: opencode-go/deepseek-v4-pro
    skills:
      - python-code-review
      - pytest
      - pytest-coverage
```

## 7. Acceptance Criteria

- **AC-001**: Given a valid `agent-project.yaml`, When `bootstrap.py validate` runs, Then it returns exit code 0 and no errors.
- **AC-002**: Given a config with an invalid `project_name`, When validated, Then it returns a specific error message naming the field and constraint violated.
- **AC-003**: Given a config listing a skill not present in `shared/skills/`, When validated, Then it returns an error with the missing skill name and expected path.
- **AC-004**: Given a config with `graph_module` pointing to a non-existent or invalid module, When validated, Then it returns an error identifying the import failure.
- **AC-005**: Given a valid config with all optional fields omitted, When manifest is generated, Then type defaults fill all omitted fields.
- **AC-006**: Given an agent with both `system_prompt` and `system_prompt_file`, When validated, Then it returns a mutual-exclusivity error.
- **AC-007**: Given an agent key containing hyphens (e.g., `my-agent`), When validated, Then it returns an error (Docker container names cannot have hyphens used as separators in subpaths).

## 8. Related Specifications

- Bootstrap CLI: `docs/specs/bootstrap-system-03-bootstrap.md`
- Container Entrypoint: `docs/specs/bootstrap-system-04-entrypoint.md`
- Skills & MCP: `docs/specs/bootstrap-system-05-skills.md`
- Overview: `docs/specs/bootstrap-system-01-overview.md`
