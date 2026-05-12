---
title: Bootstrap System — Bootstrap CLI (bootstrap.py)
version: 1.0
date_created: 2026-05-12
owner: User (direct session)
tags: [infrastructure, cli, docker, bootstrap]
---

# Introduction

`bootstrap.py` is the host-side Python CLI that reads `agent-project.yaml`,
validates it, creates Docker infrastructure, writes per-agent manifests, and
generates `docker-compose.{project}.yml`. It replaces the current
`bootstrap_project.sh` bash script.

## 1. Purpose & Scope

### Purpose
Translate a validated `agent-project.yaml` into running Docker infrastructure.
Uses the official [`docker-py`](https://docker-py.readthedocs.io/) SDK for all
Docker operations — no subprocess calls to `docker` CLI.

### Dependencies
- **Python 3.14+** (per project constraint)
- **docker** (`docker-py` package) — Docker SDK for Python
- **PyYAML** — YAML parsing
- **stdlib only otherwise** — `json`, `os`, `pathlib`, `importlib`, `sys`

### Out of Scope
- Starting containers (`docker compose up` — user does this manually or in a follow-up command)
- Governance container provisioning (separate spec)
- Multi-project orchestration (backlog)

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Docker SDK** | `docker` Python package (`import docker`), not the `docker` CLI |
| **Init container** | Short-lived `alpine:latest` container used to create directories inside volumes |
| **Subpath** | Per-agent directory inside `agent_vol` that Docker subpath-mounts |

## 3. CLI Interface

```
COMMANDS:
    bootstrap       Full pipeline: validate → volumes → seed → skills → manifests → compose
    validate        Validate agent-project.yaml only (no Docker operations)
    teardown        Remove volumes and generated compose file

Usage:
    python bootstrap.py bootstrap <config.yaml> [--compose-only] [--dry-run]
    python bootstrap.py validate <config.yaml>
    python bootstrap.py teardown <config.yaml>
```

### Command: `bootstrap`

```
ALGORITHM: bootstrap
INPUT: config_path (string), compose_only (bool, default=false), dry_run (bool, default=false)
OUTPUT: exit code 0 on success, non-zero on failure
EFFECTS:
    - Creates Docker volumes
    - Creates subdirectories inside agent_vol
    - Seeds project_vol skeleton
    - Symlinks skills from shared/skills/ to agent subpaths
    - Writes per-agent manifest.json
    - Generates docker-compose.{project}.yml

BEGIN
    -- Step 1: Load and validate
    config ← load_yaml(config_path)
    validate_config(config)  -- see §4
    project ← config["project_name"]

    IF dry_run THEN
        PRINT all actions that would be taken, then RETURN 0
    END IF

    -- Step 2: Create volumes (skip if compose_only)
    IF NOT compose_only THEN
        create_volumes(project)       -- see §5.1
        create_subdirectories(project, config)  -- see §5.2
        seed_project_volume(project)  -- see §5.3
        symlink_skills(project, config) -- see §5.4
    END IF

    -- Step 3: Write manifests
    write_manifests(project, config)  -- see §5.5

    -- Step 4: Generate compose
    compose_path ← generate_compose(project, config)  -- see §5.6

    PRINT success summary
    RETURN 0
END
```

### Command: `validate`

```
ALGORITHM: validate
INPUT: config_path (string)
OUTPUT: exit code 0 if valid, 1 if invalid (with errors on stderr)

BEGIN
    TRY
        config ← load_yaml(config_path)
    CATCH yaml.YAMLError AS e
        PRINT error: "Invalid YAML: {e}"
        RETURN 1
    END TRY
    
    errors ← validate_config(config)
    
    IF errors IS EMPTY THEN
        PRINT "Config is valid."
        RETURN 0
    ELSE
        FOR EACH error IN errors DO
            PRINT error (to stderr)
        END FOR
        RETURN 1
    END IF
END
```

### Command: `teardown`

```
ALGORITHM: teardown
INPUT: config_path (string)
OUTPUT: exit code 0 on success
EFFECTS: Removes volumes and compose file. Prompts for confirmation.

BEGIN
    config ← load_yaml(config_path)
    project ← config["project_name"]
    project_vol ← f"{project}_project_vol"
    agent_vol ← f"{project}_agent_vol"
    compose_file ← f"docker-compose.{project}.yml"
    
    PRINT f"WARNING: This will remove volumes {project_vol} and {agent_vol} and delete {compose_file}."
    PRINT "Data in volumes will be lost."
    response ← prompt("Proceed? [y/N]: ")
    
    IF response.lower() != "y" THEN
        PRINT "Aborted."
        RETURN 0
    END IF
    
    -- Remove volumes
    client ← docker.from_env()
    FOR EACH vol_name IN [project_vol, agent_vol] DO
        TRY
            vol ← client.volumes.get(vol_name)
            vol.remove(force=True)
            PRINT f"Removed volume: {vol_name}"
        CATCH docker.errors.NotFound
            PRINT f"Volume {vol_name} not found — skipping."
        END TRY
    END FOR
    
    -- Remove compose file
    IF file_exists(compose_file) THEN
        delete_file(compose_file)
        PRINT f"Removed: {compose_file}"
    END IF
    
    RETURN 0
END
```

## 4. Validation

```
ALGORITHM: validate_config
INPUT: config (dict)
OUTPUT: list of error strings (empty = valid)
DELEGATES TO: schema validation rules in bootstrap-system-02-schema.md §3

BEGIN
    errors ← []
    
    -- Top-level required fields
    IF "project_name" NOT IN config THEN
        errors.append("Missing required field: project_name")
    ELSE
        IF NOT regex_match(config["project_name"], "^[a-z][a-z0-9_-]{1,63}$") THEN
            errors.append("Invalid project_name: {config['project_name']}")
        END IF
    END IF
    
    IF "agents" NOT IN config THEN
        errors.append("Missing required field: agents")
        RETURN errors  -- cannot continue without agents
    END IF
    
    IF typeof(config["agents"]) != dict OR length(config["agents"]) == 0 THEN
        errors.append("agents must be a non-empty map")
        RETURN errors
    END IF
    
    registered_types ← {"orchestrator", "system_thinker", "implementer", "auditor", "explorer", "memory_manager", "governance"}
    
    FOR EACH agent_key, agent_def IN config["agents"].items() DO
        -- Validate key
        IF NOT regex_match(agent_key, "^[a-z][a-z0-9_]{1,30}$") THEN
            errors.append(f"Invalid agent key '{agent_key}': must be lowercase alphanumeric with underscores, 1-30 chars, no hyphens")
        END IF
        
        -- Required fields
        IF "type" NOT IN agent_def THEN
            errors.append(f"Agent '{agent_key}': missing required field 'type'")
        ELSE IF agent_def["type"] NOT IN registered_types THEN
            errors.append(f"Agent '{agent_key}': unknown type '{agent_def['type']}'. Known: {registered_types}")
        END IF
        
        IF "model" NOT IN agent_def THEN
            errors.append(f"Agent '{agent_key}': missing required field 'model'")
        ELSE IF NOT regex_match(str(agent_def["model"]), "^[a-z_]+:[a-zA-Z0-9_.-]+$") THEN
            errors.append(f"Agent '{agent_key}': model must be in provider:model-name format")
        END IF
        
        -- Mutual exclusivity
        IF "system_prompt" IN agent_def AND "system_prompt_file" IN agent_def THEN
            errors.append(f"Agent '{agent_key}': system_prompt and system_prompt_file are mutually exclusive")
        END IF
        
        -- system_prompt_file must exist
        IF "system_prompt_file" IN agent_def THEN
            IF NOT file_exists(agent_def["system_prompt_file"]) THEN
                errors.append(f"Agent '{agent_key}': system_prompt_file not found: {agent_def['system_prompt_file']}")
            END IF
        END IF
        
        -- Graph module validation (deferred import — only if graph_module specified)
        IF "graph_module" IN agent_def THEN
            TRY
                module ← importlib.import_module(agent_def["graph_module"])
                IF NOT hasattr(module, "get_graph") THEN
                    errors.append(f"Agent '{agent_key}': graph_module must expose get_graph()")
                END IF
            CATCH ImportError
                errors.append(f"Agent '{agent_key}': graph_module '{agent_def['graph_module']}' cannot be imported")
            END TRY
        END IF
        
        -- Skills validation
        IF "skills" IN agent_def THEN
            skills_dir ← Path("shared/skills")  -- relative to project root
            FOR EACH skill IN agent_def["skills"] DO
                skill_md ← skills_dir / skill / "SKILL.md"
                IF NOT file_exists(skill_md) THEN
                    errors.append(f"Agent '{agent_key}': skill '{skill}' not found at {skill_md}")
                END IF
            END FOR
        END IF
        
        -- MCP endpoint validation
        IF "mcp_endpoints" IN agent_def THEN
            endpoint_names ← set()
            FOR EACH ep IN agent_def["mcp_endpoints"] DO
                IF "name" NOT IN ep THEN
                    errors.append(f"Agent '{agent_key}': mcp_endpoint missing 'name'")
                ELSE
                    IF ep["name"] IN endpoint_names THEN
                        errors.append(f"Agent '{agent_key}': duplicate mcp_endpoint name '{ep['name']}'")
                    END IF
                    endpoint_names.add(ep["name"])
                END IF
                
                transport ← ep.get("transport")
                IF transport NOT IN {"http", "stdio"} THEN
                    errors.append(f"Agent '{agent_key}': mcp_endpoint '{ep.get('name','?')}' transport must be 'http' or 'stdio'")
                END IF
                
                IF transport == "http" AND "url" NOT IN ep THEN
                    errors.append(f"Agent '{agent_key}': mcp_endpoint '{ep['name']}' missing 'url' (required for http transport)")
                END IF
                
                IF transport == "stdio" AND "command" NOT IN ep THEN
                    errors.append(f"Agent '{agent_key}': mcp_endpoint '{ep['name']}' missing 'command' (required for stdio transport)")
                END IF
            END FOR
        END IF
        
        -- interrupt_on validation
        IF "interrupt_on" IN agent_def THEN
            FOR EACH tool_name, policy IN agent_def["interrupt_on"].items() DO
                IF typeof(policy) == dict THEN
                    allowed ← policy.get("allowed_decisions", [])
                    valid_decisions ← {"approve", "reject", "edit"}
                    FOR EACH decision IN allowed DO
                        IF decision NOT IN valid_decisions THEN
                            errors.append(f"Agent '{agent_key}': invalid interrupt_on decision '{decision}' for tool '{tool_name}'")
                        END IF
                    END FOR
                END IF
                -- bool(true) is always valid
            END FOR
        END IF
    END FOR
    
    RETURN errors
END
```

## 5. Bootstrap Operations

### 5.1 Volume Creation

```
ALGORITHM: create_volumes
INPUT: project_name (string)
OUTPUT: None
EFFECTS: Creates {project}_project_vol and {project}_agent_vol if they don't exist
DEPS: docker.from_env()

BEGIN
    client ← docker.from_env()
    project_vol ← f"{project_name}_project_vol"
    agent_vol ← f"{project_name}_agent_vol"
    
    FOR EACH vol_name IN [project_vol, agent_vol] DO
        TRY
            client.volumes.get(vol_name)
            PRINT f"Volume '{vol_name}' already exists — skipping."
        CATCH docker.errors.NotFound
            client.volumes.create(name=vol_name, driver="local")
            PRINT f"Volume '{vol_name}' created."
        END TRY
    END FOR
END
```

### 5.2 Subdirectory Pre-Creation

```
ALGORITHM: create_subdirectories
INPUT: project_name (string), config (dict)
OUTPUT: None
EFFECTS: Creates per-agent subdirectories inside agent_vol using alpine init container
DEPS: docker.from_env()

NOTE: Docker does NOT auto-create subpaths. Directories must pre-exist in the
      volume before containers with subpath: mounts can start.

BEGIN
    client ← docker.from_env()
    agent_vol ← f"{project_name}_agent_vol"
    
    -- Collect all agent keys
    subdirs ← list(config["agents"].keys())
    
    -- Build shell command to mkdir each subdir + skills/ children
    cmds ← []
    FOR EACH subdir IN subdirs DO
        cmds.append(f"mkdir -p /vol/{subdir}/skills")
        cmds.append(f"mkdir -p /vol/{subdir}/tools")
    END FOR
    cmds.append("echo 'Subdirectories created.'")
    
    command ← " && ".join(cmds)
    
    client.containers.run(
        image="alpine:latest",
        command=["sh", "-c", command],
        volumes={agent_vol: {"bind": "/vol", "mode": "rw"}},
        remove=True,
    )
    
    PRINT f"Created subdirectories in {agent_vol}: {', '.join(subdirs)}"
END
```

### 5.3 Project Volume Seeding

```
ALGORITHM: seed_project_volume
INPUT: project_name (string)
OUTPUT: None
EFFECTS: Creates skeleton directories and README in project_vol
DEPS: docker.from_env()

BEGIN
    client ← docker.from_env()
    project_vol ← f"{project_name}_project_vol"
    
    command ← (
        "mkdir -p /vol/shared/skills && "
        "mkdir -p /vol/shared/knowledge && "
        "mkdir -p /vol/shared/config && "
        f"echo '# Project: {project_name}' > /vol/README.md && "
        "echo 'Skeleton seeded.'"
    )
    
    client.containers.run(
        image="alpine:latest",
        command=["sh", "-c", command],
        volumes={project_vol: {"bind": "/vol", "mode": "rw"}},
        remove=True,
    )
    
    PRINT f"Seeded project volume: {project_vol}"
END
```

### 5.4 Skills Symlinking

Deferred to `bootstrap-system-05-skills.md` §3. Bootstrap calls `symlink_skills(project, config)` which:

```
ALGORITHM: symlink_skills
INPUT: project_name (string), config (dict)
OUTPUT: None
EFFECTS: For each agent, symlinks allowed skills from shared/skills/ into agent's skills/ subpath
DEPS: docker.from_env()

-- Uses an alpine container with the agent_vol mounted to create symlinks
-- Target skills are read from shared/skills on project_vol (mounted RO)
-- Symlinks are relative (../../shared/skills/{name} -> /workspace/skills/{name})

BEGIN
    client ← docker.from_env()
    agent_vol ← f"{project_name}_agent_vol"
    project_vol ← f"{project_name}_project_vol"
    
    FOR EACH agent_key, agent_def IN config["agents"].items() DO
        skills ← agent_def.get("skills", [])
        IF skills IS EMPTY THEN CONTINUE
        END IF
        
        cmds ← []
        FOR EACH skill IN skills DO
            -- Relative symlink from agent subpath to shared skills
            target ← f"../../shared/skills/{skill}"
            link ← f"/agent_vol/{agent_key}/skills/{skill}"
            cmds.append(f"ln -sfn {target} {link}")
        END FOR
        command ← " && ".join(cmds)
        
        IF cmds IS NOT EMPTY THEN
            client.containers.run(
                image="alpine:latest",
                command=["sh", "-c", command],
                volumes={
                    agent_vol: {"bind": "/agent_vol", "mode": "rw"},
                    project_vol: {"bind": "/shared", "mode": "ro"},
                },
                remove=True,
            )
        END IF
    END FOR
    
    PRINT "Skills symlinked."
END
```

### 5.5 Manifest Writing

```
ALGORITHM: write_manifests
INPUT: project_name (string), config (dict)
OUTPUT: None
EFFECTS: Writes per-agent manifest.json files into agent_vol subpaths
DEPS: docker.from_env()

TYPE_DEFAULTS = {
    "orchestrator": {
        "system_prompt": "You are the project orchestrator. Delegate tasks, never execute directly.",
        "graph_module": "agents.orchestrator.graph",
        "skills": ["planning-with-files"],
    },
    "system_thinker": {
        "system_prompt": "You are a domain design specialist. Produce design options and pseudocode specs.",
        "graph_module": "agents.system_thinker.graph",
        "skills": ["sequential-thinking"],
    },
    "implementer": {
        "system_prompt": "You are a code translator. Read approved specs, write production code.",
        "graph_module": "agents.implementer.graph",
        "skills": ["python-expert"],
    },
    "auditor": {
        "system_prompt": "You are a code auditor. Examine code across 5 dimensions.",
        "graph_module": "agents.auditor.graph",
        "skills": ["python-code-review"],
    },
    "explorer": {
        "system_prompt": "You are a codebase scout. Read-only structural analysis.",
        "graph_module": "agents.explorer.graph",
        "skills": [],
    },
    "memory_manager": {
        "system_prompt": "You are a memory ingestion pipeline. Validate, embed, store.",
        "graph_module": "agents.memory_manager.graph",
        "skills": ["langchain-rag", "qdrant-vector-search"],
    },
    "governance": {
        "system_prompt": "You are the governance MCP server. Manage agents and proxy MCP requests.",
        "graph_module": "agents.governance.graph",
        "skills": [],
    },
}

BEGIN
    FOR EACH agent_key, agent_def IN config["agents"].items() DO
        agent_type ← agent_def["type"]
        defaults ← TYPE_DEFAULTS.get(agent_type, {})
        
        -- Merge: config overrides > type defaults
        manifest ← {
            "agent_key": agent_key,
            "type": agent_type,
            "model": agent_def["model"],
            "system_prompt": agent_def.get("system_prompt")
                or agent_def.get("system_prompt_file")  -- resolved at entrypoint time
                or defaults.get("system_prompt", ""),
            "system_prompt_file": agent_def.get("system_prompt_file", None),
            "graph_module": agent_def.get("graph_module", defaults.get("graph_module", None)),
            "skills": agent_def.get("skills", defaults.get("skills", [])),
            "mcp_endpoints": agent_def.get("mcp_endpoints", []),
            "interrupt_on": agent_def.get("interrupt_on", {}),
            "permissions": agent_def.get("permissions", []),
            "workspace_path": "/workspace",
            "project_path": "/app/project",
            "skills_path": f"/workspace/skills",
        }
        
        manifest_json ← json.dumps(manifest, indent=2)
        
        -- Write via alpine init container
        client ← docker.from_env()
        agent_vol ← f"{project_name}_agent_vol"
        
        -- Create temp file with manifest content, then copy into volume
        -- (Alternative: write to a bind-mounted temp dir)
        -- Using a here-doc in shell:
        escaped ← manifest_json.replace("'", "'\\''")
        command ← f"cat > /vol/{agent_key}/manifest.json << 'MANIFEST_EOF'\n{manifest_json}\nMANIFEST_EOF"
        
        client.containers.run(
            image="alpine:latest",
            command=["sh", "-c", command],
            volumes={agent_vol: {"bind": "/vol", "mode": "rw"}},
            remove=True,
        )
    END FOR
    
    PRINT f"Manifests written for {len(config['agents'])} agents."
END
```

### 5.6 Compose Generation

```
ALGORITHM: generate_compose
INPUT: project_name (string), config (dict)
OUTPUT: compose_path (string) — path to generated file
EFFECTS: Writes docker-compose.{project}.yml

BEGIN
    project_vol ← f"{project_name}_project_vol"
    agent_vol ← f"{project_name}_agent_vol"
    compose_file ← f"docker-compose.{project_name}.yml"
    
    -- Build agent service blocks
    agent_services ← ""
    FOR EACH agent_key IN config["agents"].keys() DO
        read_only ← (agent_key != "orchestrator")  -- orchestrator gets RW on project_vol
        ro_str ← "true" IF read_only ELSE "false"
        
        agent_services += f"""
  {agent_key}:
    image: langgraph-agent-base:latest
    container_name: {project_name}_{agent_key}
    volumes:
      - type: volume
        source: {project_vol}
        target: /app/project
        read_only: {ro_str}
      - type: volume
        source: {agent_vol}
        target: /workspace
        volume:
          subpath: {agent_key}
    networks:
      - agent_net
"""
    END FOR
    
    compose_yaml ← f"""# Agentic Docker Stack — {project_name}
# Generated by bootstrap.py — do not edit manually
# Source: agent-project.yaml

services:
  orchestrator:
    image: langgraph-agent-base:latest
    container_name: {project_name}_orchestrator
    volumes:
      - type: volume
        source: {project_vol}
        target: /app/project
        read_only: false
      - type: volume
        source: {agent_vol}
        target: /workspace
        volume:
          subpath: orchestrator
    networks:
      - agent_net
{agent_services}
networks:
  agent_net:
    driver: bridge
    name: {project_name}_agent_net

volumes:
  {project_vol}:
    external: true
  {agent_vol}:
    external: true
"""
    
    write_file(compose_file, compose_yaml)
    
    PRINT f"Generated: {compose_file}"
    RETURN compose_file
END
```

**Note on orchestrator:** The above generates orchestrator as a regular agent service.
The config MUST include an `orchestrator` key in `agents:`. If it doesn't, validation
fails. The orchestrator gets `read_only: false` on `project_vol`; all other agents get
`read_only: true`.

**Note on governance:** Governance is NOT included in the generated compose. Once the
governance spec is written, a future version of this spec will add it. For MVP,
governance runs separately or is manually added to the compose.

## 6. Error Handling

| Error Condition | Behavior |
|----------------|---------|
| YAML parse failure | Print line number + error, exit 1 |
| Docker daemon not running | Print "Cannot connect to Docker daemon. Is Docker running?" + exit 1 |
| Volume already exists | Print "already exists — skipping" (not an error) |
| Volume creation fails | Print error message from Docker SDK, exit 1 |
| Init container fails | Print container logs + exit 1 |
| Compose file write fails | Print OS error + exit 1 |
| Any validation error | Collect all errors, print each, exit 1 |

## 7. Acceptance Criteria

- **AC-008**: Given a valid config with 3 agents, When `bootstrap` runs, Then 2 volumes exist, 3 subdirectories exist in agent_vol, project_vol has skeleton, 3 manifest.json files exist, and compose file is valid YAML.
- **AC-009**: Given existing volumes, When `bootstrap` runs again, Then volumes are NOT recreated, subdirectories are NOT duplicated, manifests are overwritten.
- **AC-010**: Given `--dry-run`, When `bootstrap` runs, Then NO volumes, files, or directories are created, but all planned actions are printed.
- **AC-011**: Given an invalid config, When `validate` runs, Then all validation errors are collected and printed, exit code is 1.
- **AC-012**: Given the generated compose file, When `docker compose -f {file} config` runs, Then YAML parses without errors.
- **AC-013**: Given `teardown` and user confirms "y", When it runs, Then volumes are removed and compose file is deleted.
- **AC-014**: Given `teardown` and user confirms "n", When it runs, Then nothing is changed.

## 8. Related Specifications

- Schema: `docs/specs/bootstrap-system-02-schema.md`
- Entrypoint: `docs/specs/bootstrap-system-04-entrypoint.md`
- Skills & MCP: `docs/specs/bootstrap-system-05-skills.md`
- Overview: `docs/specs/bootstrap-system-01-overview.md`
- Current bash bootstrap: `docs/plans/overhaul/bootstrap_project.sh`
