---
title: Bootstrap System — Skills Symlinking & MCP Proxying
version: 1.0
date_created: 2026-05-12
owner: User (direct session)
tags: [skills, mcp, governance, security, symlink]
---

# Introduction

Skills and MCP endpoints are the two primary capability-injection mechanisms for agents.
Skills are symlinked from a shared volume into per-agent subpaths at bootstrap time.
MCP endpoints are proxied through the governance container (build phase) or connected
directly (post-build phase). This spec defines both models.

## 1. Purpose & Scope

### Skills
- Define the skills directory layout on `project_vol`
- Define the symlink model used at bootstrap time
- Define the SKILL.md validation requirements
- Define the runtime skill loading path inside the container

### MCP Proxying
- Define the two-phase MCP access model (proxy → router)
- Define how governance proxies MCP requests for agents
- Define the per-agent MCP endpoint allowlist in manifest
- Define how the container entrypoint routes MCP through governance (build phase)

### Out of Scope
- Governance container implementation (separate spec)
- Multi-user skill management
- Skill versioning or upgrades
- MCP endpoint health monitoring

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Skill** | A directory in `shared/skills/` containing a `SKILL.md` with YAML frontmatter |
| **Symlink** | A filesystem link from agent's `skills/{name}` → `../../shared/skills/{name}` |
| **Allowlist** | The set of skills an agent is permitted to load, defined in manifest |
| **MCP Proxy** | Governance intercepts and forwards MCP requests from agents to external endpoints |
| **MCP Router** | Governance publishes endpoint registries; agents connect directly (post-build phase) |
| **Build Phase** | Early development: governance is sole MCP proxy |
| **Post-Build Phase** | Mature system: agents have their own MCP servers; governance is a registry |

## 3. Skills Symlinking Model

### 3.1 Directory Layout

```
project_vol (mounted at /app/project in containers)
└── shared/
    └── skills/
        ├── planning-with-files/
        │   └── SKILL.md
        ├── langchain-rag/
        │   └── SKILL.md
        ├── qdrant-vector-search/
        │   └── SKILL.md
        ├── python-expert/
        │   └── SKILL.md
        └── ...
```

```
agent_vol (mounted at /workspace in containers)
├── orchestrator/
│   ├── manifest.json
│   └── skills/
│       ├── planning-with-files -> ../../shared/skills/planning-with-files
│       └── sequential-thinking -> ../../shared/skills/sequential-thinking
├── memory_manager/
│   ├── manifest.json
│   └── skills/
│       ├── langchain-rag -> ../../shared/skills/langchain-rag
│       └── qdrant-vector-search -> ../../shared/skills/qdrant-vector-search
└── ...
```

### 3.2 Symlink Creation (Bootstrap-Time)

```
ALGORITHM: create_skill_symlinks
INPUT: agent_vol (string), project_vol (string), agent_key (string), allowed_skills (list[string])
OUTPUT: None
EFFECTS: Creates symlinks in agent's skills/ subpath

DELEGATED FROM: bootstrap-system-03-bootstrap.md §5.4

BEGIN
    skills_dir_on_agent ← f"{agent_key}/skills"
    shared_skills ← "shared/skills"
    
    FOR EACH skill IN allowed_skills DO
        source ← f"../../{shared_skills}/{skill}"  -- relative from agent subpath root
        target ← f"{skills_dir_on_agent}/{skill}"
        
        -- Create symlink inside the agent_vol
        -- Uses an alpine init container because the host may not have ln
        SYMLINK_CMD: f"ln -sfn {source} {target}"
    END FOR
    
    -- The symlink resolves at container runtime because both volumes
    -- are mounted in the container:
    --   /workspace/{agent_key}/skills/{skill}
    --     -> ../../shared/skills/{skill}
    --     -> /workspace/../shared/skills/{skill}
    --     -> /app/project/shared/skills/{skill}  (via project_vol mount)
END
```

### 3.3 Runtime Skill Loading

Inside the container, the entrypoint passes `skills=["/workspace/skills"]` to
`create_deep_agent()`. Deep Agents' `SkillsMiddleware` scans this directory for
`SKILL.md` files and loads them on-demand.

```
CONTAINER FILESYSTEM (at runtime):
    /workspace/                     ← agent_vol subpath mount
    ├── manifest.json
    └── skills/                     ← symlinks to /app/project/shared/skills/
        ├── langchain-rag -> ../../shared/skills/langchain-rag
        │   └── resolves to /app/project/shared/skills/langchain-rag/SKILL.md
        └── qdrant-vector-search -> ../../shared/skills/qdrant-vector-search
            └── resolves to /app/project/shared/skills/qdrant-vector-search/SKILL.md
    
    /app/project/                   ← project_vol mount (RO for agents)
    └── shared/
        └── skills/
            ├── langchain-rag/SKILL.md
            └── qdrant-vector-search/SKILL.md
```

### 3.4 SKILL.md Validation

Before symlinking, bootstrap validates each skill file:

```
ALGORITHM: validate_skill_file
INPUT: skill_path (path to SKILL.md)
OUTPUT: ok or error

BEGIN
    IF NOT file_exists(skill_path) THEN
        RETURN error("SKILL.md not found at {skill_path}")
    END IF
    
    content ← read_file(skill_path)
    
    -- Must start with YAML frontmatter (--- on line 1)
    IF NOT content STARTS WITH "---\n" THEN
        RETURN error("SKILL.md at {skill_path} missing YAML frontmatter")
    END IF
    
    -- Must have a closing ---
    second_delimiter ← find(content, "\n---", start=4)
    IF second_delimiter IS None THEN
        RETURN error("SKILL.md at {skill_path} has unclosed frontmatter")
    END IF
    
    -- Extract and parse frontmatter
    frontmatter_text ← content[4:second_delimiter]
    TRY
        frontmatter ← yaml.safe_load(frontmatter_text)
    CATCH yaml.YAMLError
        RETURN error("SKILL.md at {skill_path} has invalid YAML frontmatter")
    END TRY
    
    -- Required fields
    IF "name" NOT IN frontmatter THEN
        RETURN error("SKILL.md at {skill_path} missing 'name' in frontmatter")
    END IF
    IF "description" NOT IN frontmatter THEN
        RETURN error("SKILL.md at {skill_path} missing 'description' in frontmatter")
    END IF
    
    RETURN ok
END
```

## 4. MCP Proxying Model

### 4.1 Two-Phase Model

| Phase | Governance Role | Agent MCP Connection | Config |
|-------|----------------|---------------------|--------|
| **Build** (MVP) | Proxy — all agent MCP requests route through governance | Agent → Governance → External MCP | `mcp_endpoints` in manifest point to governance |
| **Post-Build** (future) | Router — publishes registries, authorizes direct connections | Agent → External MCP (direct, with governance authorization) | `mcp_endpoints` point to actual servers |

### 4.2 Build Phase: Agent → Governance Proxy

```
REQUEST FLOW:
    Agent Container                    Governance Container           External MCP
    ─────────────                      ────────────────────           ─────────────
    create_deep_agent()                
      → MultiServerMCPClient({         
          "qdrant": {                  
            transport: "http",         
            url: "http://governance:8000/mcp/proxy/qdrant"
          }                             
        })                             
            │                                    │
            │── GET /mcp/proxy/qdrant ──────────►│
            │                                    │── Forward to http://qdrant:6333 ──►
            │                                    │◄── Response ───────────────────────
            │◄── Response ──────────────────────│
```

**Manifest config for build phase:**
```json
{
    "mcp_endpoints": [
        {
            "name": "qdrant",
            "transport": "http",
            "url": "http://governance:8000/mcp/proxy/qdrant"
        },
        {
            "name": "lite_llm",
            "transport": "http",
            "url": "http://governance:8000/mcp/proxy/lite_llm"
        }
    ]
}
```

All endpoint URLs point to governance. Governance's proxy tool maps the path suffix
(`/qdrant`, `/lite_llm`) to the actual endpoint URL from its own configuration.
The agent never knows the real endpoint address.

### 4.3 Per-Agent Endpoint Allowlist

Governance enforces which MCP endpoints each agent can access. The allowlist is in the
agent's manifest:

```json
{
    "mcp_endpoints": [
        {"name": "qdrant", "transport": "http", "url": "http://governance:8000/mcp/proxy/qdrant"},
        {"name": "lite_llm", "transport": "http", "url": "http://governance:8000/mcp/proxy/lite_llm"}
    ]
}
```

At governance level, a separate configuration maps agent identities to allowed endpoints:

```yaml
# governance config (separate spec — shown here for context only)
agent_endpoint_allowlist:
  memory_manager:
    - qdrant
    - lite_llm
  orchestrator:
    - governance
  implementer:
    - governance
```

Governance rejects proxy requests for endpoints not in the agent's allowlist with a
403 Forbidden.

### 4.4 MVP Simplification

For MVP, the governance container is NOT yet implemented. The bootstrap-generated
manifest uses **direct endpoint URLs** — agents connect to Qdrant, LiteLLM, etc.
directly without going through a proxy:

```json
{
    "mcp_endpoints": [
        {"name": "qdrant", "transport": "http", "url": "http://qdrant:6333"},
        {"name": "lite_llm", "transport": "http", "url": "http://lite_llm:4000"}
    ]
}
```

This is the MVP compromise: same manifest schema, same entrypoint logic, but the
URL points to the real server. When governance is implemented, the manifest URL
changes to the governance proxy. No entrypoint code change needed.

### 4.5 Post-Build Phase (Future): Router Model

When agents have their own MCP servers:
1. Agent registers its MCP endpoints with governance at startup
2. Governance publishes an endpoint registry
3. Other agents discover endpoints via governance's registry
4. Agents connect directly (authorization tokens from governance)
5. Governance retains ability to revoke access

This model is NOT in scope for this spec. Included for architectural context only.

## 5. Runtime MCP Tool Loading

The container entrypoint (`bootstrap-system-04-entrypoint.md` §3, `load_mcp_tools`)
handles MCP tool loading at startup:

```
CONCEPTUAL FLOW:
    1. Read mcp_endpoints from manifest.json
    2. For each endpoint, build MultiServerMCPClient config
    3. If in build phase: URLs point to governance proxy
       If in MVP: URLs point to actual servers directly
    4. client.get_tools() loads all tools from all endpoints
    5. Pass tools to create_deep_agent(tools=...)
```

The entrypoint does NOT need to know which phase it's in. It just uses whatever URLs
are in the manifest. The phase is determined by what `bootstrap.py` writes into the
manifest.

## 6. Skills vs. MCP Tools — Distinction

| | Skills | MCP Tools |
|---|---|---|
| **What they are** | Instruction documents (SKILL.md) | Executable functions from external servers |
| **How loaded** | Deep Agents `skills=[...]` → SkillsMiddleware reads SKILL.md | `MultiServerMCPClient.get_tools()` → injected as `tools=[...]` |
| **When loaded** | On-demand (progressive disclosure) | At agent startup (all loaded) |
| **Storage** | `shared/skills/` on project_vol | External servers (Qdrant, LiteLLM, governance) |
| **Per-agent control** | Symlink at bootstrap time | Manifest `mcp_endpoints` list |
| **Governance role** | None (orchestrator manages allowlist) | Proxies requests (build phase) or authorizes (post-build) |

## 7. Acceptance Criteria

- **AC-022**: Given an agent config with `skills: [langchain-rag]`, When bootstrap runs, Then a symlink `{agent_subpath}/skills/langchain-rag -> ../../shared/skills/langchain-rag` exists.
- **AC-023**: Given a `SKILL.md` without frontmatter, When validated, Then bootstrap reports an error.
- **AC-024**: Given a `SKILL.md` with frontmatter but no `name` field, When validated, Then bootstrap reports an error.
- **AC-025**: Given an agent with 3 skills in config, When bootstrap runs, Then exactly 3 symlinks exist; no extra symlinks.
- **AC-026**: Given a manifest with MCP endpoint URL pointing to governance proxy, When the entrypoint loads MCP tools, Then `MultiServerMCPClient` connects to the proxy URL.
- **AC-027**: Given a manifest with MCP endpoint URL pointing directly to Qdrant, When the entrypoint loads MCP tools, Then `MultiServerMCPClient` connects to Qdrant directly (MVP mode).
- **AC-028**: Given an agent config with `skills: []`, When bootstrap runs, Then no skills/ directory is created for that agent (or it's empty).

## 8. Related Specifications

- Overview: `docs/specs/bootstrap-system-01-overview.md`
- Schema: `docs/specs/bootstrap-system-02-schema.md`
- Bootstrap CLI: `docs/specs/bootstrap-system-03-bootstrap.md`
- Entrypoint: `docs/specs/bootstrap-system-04-entrypoint.md`
- Architecture: `docs/plans/overhaul/MASTER_STATUS.md` §8 (MCP endpoint access delegation)
- Docker architecture chat: `docs/plans/overhaul/docker_architecture_chat.md`
