---
title: Bootstrap System — Agent Container Entrypoint
version: 1.0
date_created: 2026-05-12
owner: User (direct session)
tags: [runtime, container, agent, acp, langgraph]
---

# Introduction

The container entrypoint (`entrypoint.py`) runs inside every agent container at startup.
It reads the per-agent `manifest.json`, loads the compiled LangGraph graph (if any),
loads MCP tools, creates a Deep Agent, and exposes it over ACP.

## 1. Purpose & Scope

### Purpose
Given a `manifest.json` at `/workspace/manifest.json`, produce a running ACP server
backed by a configured `create_deep_agent()` instance. The entrypoint is the same
script for all agent types — differences come from the manifest.

### In-Scope
- Manifest reading and parsing
- Graph module loading (with `get_graph()`)
- MCP tool loading via `MultiServerMCPClient`
- System prompt resolution (inline, file, or type default)
- `create_deep_agent()` invocation with all manifest-derived parameters
- ACP server wrap + `run_agent()`

### Out of Scope
- Tool function definitions (deferred)
- Checkpointer/Store selection logic (hardcoded to `MemorySaver` / `InMemoryStore` for MVP)
- Governance proxy awareness (agent connects to MCP endpoints directly for MVP; governance proxy added later per `bootstrap-system-05-skills.md`)
- Health checks, metrics, logging infrastructure

### Dependencies (in container image)
- `deepagents` — `create_deep_agent`
- `deepagents-acp` — `AgentServerACP`
- `acp` — `run_agent`
- `langchain-mcp-adapters` — `MultiServerMCPClient`
- `langgraph-checkpoint` — `MemorySaver` (MVP; PostgresSaver for production)
- `langgraph-store` — `InMemoryStore` (MVP; PostgresStore for production)

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Manifest** | JSON file at `/workspace/manifest.json` written by bootstrap |
| **Graph module** | Python module with `get_graph() -> CompiledStateGraph` |
| **MCP tools** | LangChain tools loaded from MCP server endpoints |
| **ACP** | Agent Client Protocol — stdio transport for editor-agent communication |

## 3. Entrypoint Algorithm

```
ALGORITHM: main
INPUT: (none — reads /workspace/manifest.json)
OUTPUT: Running ACP server (blocks until termination)
ENV DEPS: See §6

BEGIN
    -- Step 1: Load manifest
    manifest_path ← "/workspace/manifest.json"
    IF NOT file_exists(manifest_path) THEN
        PRINT error: "manifest.json not found at {manifest_path}"
        EXIT 1
    END IF
    
    manifest ← json.loads(read_file(manifest_path))
    
    -- Step 2: Resolve system prompt
    system_prompt ← resolve_system_prompt(manifest)
    
    -- Step 3: Load custom tools (from graph module, if any)
    graph_tools ← load_graph_tools(manifest)
    
    -- Step 4: Load MCP tools
    mcp_tools ← await load_mcp_tools(manifest)
    
    -- Step 5: Merge all tools
    all_tools ← graph_tools + mcp_tools
    
    -- Step 6: Resolve skills path
    skills_path ← manifest.get("skills_path", "/workspace/skills")
    
    -- Step 7: Create Deep Agent
    agent ← create_agent_instance(
        manifest=manifest,
        tools=all_tools,
        system_prompt=system_prompt,
        skills_path=skills_path,
    )
    
    -- Step 8: Expose over ACP
    server ← AgentServerACP(agent)
    await run_agent(server)
    
    -- run_agent() blocks; agent runs until the container stops
END

ALGORITHM: resolve_system_prompt
INPUT: manifest (dict)
OUTPUT: system_prompt (string)

BEGIN
    -- Priority: inline > file > type default (already merged in manifest)
    IF manifest.get("system_prompt_file") IS NOT None THEN
        prompt_path ← manifest["system_prompt_file"]
        -- Inside container, prompt files are at /app/project/{path}
        container_path ← Path("/app/project") / prompt_path
        IF file_exists(container_path) THEN
            RETURN read_file(container_path)
        ELSE
            PRINT warning: "system_prompt_file not found at {container_path}, using fallback"
        END IF
    END IF
    
    IF manifest.get("system_prompt") THEN
        RETURN manifest["system_prompt"]
    END IF
    
    -- Fallback: generic prompt from type
    RETURN f"You are a {manifest['type']} agent. Follow your system instructions."
END

ALGORITHM: load_graph_tools
INPUT: manifest (dict)
OUTPUT: tools (list of LangChain Tool objects)

BEGIN
    graph_module_path ← manifest.get("graph_module")
    IF graph_module_path IS None THEN
        RETURN []
    END IF
    
    TRY
        module ← importlib.import_module(graph_module_path)
        graph ← module.get_graph()
        
        -- Extract tools from the compiled graph if available
        -- For agents with a custom graph, tools may be embedded in the graph
        -- or the module may expose a get_tools() function
        IF hasattr(module, "get_tools") THEN
            RETURN module.get_tools()
        END IF
        
        PRINT log: f"Graph loaded from {graph_module_path} (no custom tools exposed)"
        RETURN []
    CATCH Exception AS exc
        PRINT error: f"Failed to load graph module {graph_module_path}: {exc}"
        RETURN []
    END TRY
END

ALGORITHM: load_mcp_tools
INPUT: manifest (dict)
OUTPUT: tools (list of LangChain Tool objects)

BEGIN
    mcp_endpoints ← manifest.get("mcp_endpoints", [])
    IF mcp_endpoints IS EMPTY THEN
        RETURN []
    END IF
    
    -- Build MultiServerMCPClient config from manifest
    server_config ← {}
    FOR EACH ep IN mcp_endpoints DO
        config_entry ← {"transport": ep["transport"]}
        IF ep["transport"] == "http" THEN
            config_entry["url"] ← ep["url"]
            IF "headers" IN ep THEN
                config_entry["headers"] ← ep["headers"]
            END IF
        ELSE IF ep["transport"] == "stdio" THEN
            config_entry["command"] ← ep["command"]
            IF "args" IN ep THEN
                config_entry["args"] ← ep["args"]
            END IF
        END IF
        server_config[ep["name"]] ← config_entry
    END FOR
    
    TRY
        client ← MultiServerMCPClient(server_config)
        tools ← await client.get_tools()
        PRINT log: f"Loaded {len(tools)} MCP tools from {len(mcp_endpoints)} endpoints"
        RETURN tools
    CATCH Exception AS exc
        PRINT error: f"Failed to load MCP tools: {exc}"
        -- Non-fatal: agent starts without MCP tools, reports error
        RETURN []
    END TRY
END

ALGORITHM: create_agent_instance
INPUT: manifest (dict), tools (list), system_prompt (string), skills_path (string)
OUTPUT: CompiledStateGraph (the deep agent)

BEGIN
    -- Base parameters
    agent_kwargs ← {
        "model": manifest["model"],
        "tools": tools,
        "system_prompt": system_prompt,
        "name": manifest["agent_key"],
    }
    
    -- Skills
    IF manifest.get("skills") AND len(manifest["skills"]) > 0 THEN
        agent_kwargs["skills"] ← [skills_path]
    END IF
    
    -- HITL (interrupt_on)
    interrupt_on ← manifest.get("interrupt_on", {})
    IF interrupt_on IS NOT EMPTY THEN
        agent_kwargs["interrupt_on"] ← interrupt_on
    END IF
    
    -- Permissions (filesystem)
    permissions ← manifest.get("permissions", [])
    IF permissions IS NOT EMPTY THEN
        -- Convert to FilesystemPermission objects
        fs_permissions ← []
        FOR EACH perm IN permissions DO
            fs_permissions.append(FilesystemPermission(
                path=perm["path"],
                read=perm.get("read", True),
                write=perm.get("write", False),
            ))
        END FOR
        agent_kwargs["permissions"] ← fs_permissions
    END IF
    
    -- Backend (FilesystemBackend with workspace root)
    from deepagents.backends import FilesystemBackend
    workspace_root ← manifest.get("workspace_path", "/workspace")
    agent_kwargs["backend"] ← FilesystemBackend(
        root_dir=workspace_root,
        virtual_mode=True,
    )
    
    -- Checkpointer (MVP: MemorySaver)
    from langgraph.checkpoint.memory import MemorySaver
    agent_kwargs["checkpointer"] ← MemorySaver()
    
    -- Store (MVP: InMemoryStore)
    from langgraph.store.memory import InMemoryStore
    agent_kwargs["store"] ← InMemoryStore()
    
    -- Create the agent
    TRY
        agent ← create_deep_agent(**agent_kwargs)
        PRINT log: f"Agent '{manifest['agent_key']}' created successfully"
        RETURN agent
    CATCH Exception AS exc
        PRINT error: f"Failed to create agent: {exc}"
        EXIT 1
    END TRY
END
```

## 4. Full Entrypoint Script Structure

```
FILE: entrypoint.py
LOCATION: In the langgraph-agent-base Docker image at /app/entrypoint.py
TRIGGER: Container CMD or ENTRYPOINT

MODULE STRUCTURE:
    main()                    — async entry point
    resolve_system_prompt()   — prompt resolution
    load_graph_tools()        — import graph module, extract tools
    load_mcp_tools()          — MultiServerMCPClient tool loading
    create_agent_instance()   — create_deep_agent() invocation
    -- Entry guard --
    if __name__ == "__main__":
        asyncio.run(main())
```

## 5. Graph Module Contract

Any module referenced by `graph_module` in the manifest MUST expose:

```python
# Required
def get_graph() -> CompiledStateGraph:
    """Return the compiled LangGraph StateGraph for this agent."""
    ...

# Optional — if the graph has custom tools to expose to create_deep_agent
def get_tools() -> list:
    """Return LangChain tools that the agent needs beyond MCP-loaded ones."""
    ...
```

### Example: memory_manager

```python
# agents/memory_manager/graph.py
from langgraph.graph.state import CompiledStateGraph

def get_graph() -> CompiledStateGraph:
    """3-node ingestion pipeline: validate → build → embed."""
    return _build_and_compile()

def get_tools() -> list:
    """Expose the ingest() function as a tool for the orchestrator to call."""
    from langchain_core.tools import tool
    
    @tool
    def ingest_memory(content: str, source: str, category_type: str = None, 
                      category: str = None, tags: list[str] = None) -> dict:
        """Ingest a memory chunk into the vector store."""
        from . import ingest
        result = ingest(content, source, category_type, category, tags)
        return result.model_dump()
    
    return [ingest_memory]
```

## 6. Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `LITELLM_API_KEY` | YES | API key for LiteLLM proxy (embeddings + classification) |
| `LITE_LLM_URL` | NO | LiteLLM proxy URL (default: `http://lite_llm:4000`) |
| `QDRANT_URL` | NO | Qdrant URL (default: `http://qdrant:6333`) |
| `QDRANT_COLLECTION` | NO | Qdrant collection name (default: `memory_chunks`) |
| `ANTHROPIC_API_KEY` | NO | If using Anthropic models |
| `OPENAI_API_KEY` | NO | If using OpenAI models |
| `LOG_LEVEL` | NO | Python logging level (default: `INFO`) |

**Constraint:** No hardcoded secrets in the image or manifest. All credentials via env vars.

## 7. Error Handling

| Error Condition | Behavior |
|----------------|---------|
| `manifest.json` not found | Log error, exit 1 |
| Graph module import fails | Log error, continue without graph (non-fatal if tools from MCP) |
| Graph module has no `get_graph()` | Log error, continue (agent may still function with prompt+tools only) |
| MCP endpoint unreachable | Log warning, continue without those tools |
| MCP tool loading fails entirely | Log error, agent starts without MCP tools (non-fatal) |
| `create_deep_agent()` fails | Log error, exit 1 (fatal) |
| `run_agent()` fails | Log error, exit 1 (fatal) |
| Model API key missing | `create_deep_agent()` fails at first LLM call; exit 1 |

**Design rule:** Missing MCP tools or graph modules are NON-FATAL. The agent starts with whatever it can load. Only `create_deep_agent()` failure is fatal.

## 8. ACP Exposure Notes

```python
from acp import run_agent
from deepagents_acp.server import AgentServerACP

server = AgentServerACP(agent)
await run_agent(server)
```

### Current Limitation
The `acp` package and `deepagents-acp` currently only document **stdio transport**
(stdin/stdout). This works for editor-launched agents but is insufficient for
Docker containers that need network-accessible endpoints.

### Future Resolution Options
1. **Check `acp` package for HTTP/SSE transport support** — the `run_agent()` function
   may accept a `transport=` parameter not yet documented.
2. **Bridge via Docker** — run stdio ACP inside container, bridge via `docker exec` /
   `docker attach` from orchestrator.
3. **Wrap in FastAPI/SSE** — create a thin HTTP wrapper around `AgentServerACP` that
   exposes `agent.invoke()` and `agent.stream()` as HTTP endpoints. This is how the
   governance MCP server is designed (FastMCP over SSE).
4. **Wait for ACP network transport spec** — the ACP protocol at
   [agentclientprotocol.com](https://agentclientprotocol.com) may add network
   transport support.

**This spec does not resolve the transport question.** It defines the agent wiring.
The transport layer is a separate design concern addressed when the orchestrator-to-agent
communication protocol is finalized.

## 9. Acceptance Criteria

- **AC-015**: Given a valid manifest with `graph_module` pointing to `src/memory/graph.py`, When the entrypoint runs, Then `get_graph()` is called and the compiled graph is available.
- **AC-016**: Given a manifest with 2 MCP endpoints (http), When the entrypoint runs, Then `MultiServerMCPClient` loads tools from both endpoints and merges them into `create_deep_agent(tools=...)`.
- **AC-017**: Given a manifest with `skills: ["langchain-rag"]`, When the entrypoint runs, Then `create_deep_agent` is called with `skills=["/workspace/skills"]`.
- **AC-018**: Given a manifest with `interrupt_on: {delete_file: true}`, When the entrypoint runs, Then `create_deep_agent` is called with matching `interrupt_on` dict.
- **AC-019**: Given a manifest with missing `graph_module`, When the entrypoint runs, Then the agent starts without graph tools (non-fatal).
- **AC-020**: Given an unreachable MCP endpoint, When the entrypoint runs, Then the agent starts without those tools and logs a warning (non-fatal).
- **AC-021**: Given a missing API key for the model provider, When the entrypoint runs, Then `create_deep_agent()` or the first LLM call fails with a clear error.

## 10. Related Specifications

- Schema: `docs/specs/bootstrap-system-02-schema.md`
- Bootstrap CLI: `docs/specs/bootstrap-system-03-bootstrap.md`
- Skills & MCP: `docs/specs/bootstrap-system-05-skills.md`
- Overview: `docs/specs/bootstrap-system-01-overview.md`
- Framework skills: `langchain-fundamentals`, `langgraph-fundamentals`, `deep-agents-core`, `deep-agents-orchestration`, `langchain-middleware`
