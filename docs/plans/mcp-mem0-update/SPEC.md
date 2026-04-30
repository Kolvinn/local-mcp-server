---
title: Goal-Tree Memory Integration Specification
version: 1.0
date_created: 2026-04-30
tags: [data, schema, tool, mcp, mem0]
---

# Introduction

Specification for integrating goal-tree operations (`goal_trees.py`) into the Mem0-backed memory service (`src/main.py`). Goal nodes are stored as Mem0 memories with specialized metadata, sharing the same `memory_client` and Qdrant collection as general memories. Five new MCP tools provide goal tree CRUD + search + tree reconstruction.

## 1. Purpose & Scope

**Purpose:** Replace the standalone `goal_trees.py` (raw Qdrant/Ollama) with Mem0-native goal-tree tools inside `main.py`, eliminating duplicate infrastructure connections and unifying the memory layer.

**Scope:**
- 5 new tools in `src/main.py`: `add_goal_node`, `search_goal_nodes`, `get_goal_tree`, `update_goal_node`, `delete_goal_node`
- Metadata schema for goal/task/subtask nodes
- Helper functions for goal-specific filter construction and tree reconstruction
- Proxy config update in `mcp-proxy-server.py`
- RBAC permission entries for new tools
- `.env` cleanup

**Out of scope:**
- Goal-keeper agent logic (merge/dedup heuristics) — this spec provides the building blocks
- Cascade delete logic — left to the calling agent
- UI or visualization
- Session collection management (dropped; Mem0 manages storage)

**Audience:** Builder/implementer agent. Read alongside `docs/context/constraints.md`, `docs/context/conventions.md`, and the existing `src/main.py` source.

## 2. Definitions

| Term | Definition |
|------|------------|
| **Goal node** | Any node in the goal tree: can be `goal`, `task`, or `subtask` |
| **Root goal** | A top-level goal with no parent (`parent_id` is null) |
| **Tree** | The hierarchical structure of nodes sharing a common `root_id` |
| **Mem0 OSS** | `from mem0 import Memory` — self-hosted, config-driven, local execution |
| **memory_client** | The global `Memory` instance in `main.py`, initialized via `Memory.from_config()` |
| **Status** | Lifecycle state: `active`, `completed`, `blocked`, `abandoned` |

## 3. Requirements, Constraints & Guidelines

### Requirements
- **REQ-001**: Goal nodes SHALL be stored via `memory_client.add()` with structured metadata
- **REQ-002**: All goal-node tools SHALL use the existing global `memory_client` (no new Qdrant/Ollama connections)
- **REQ-003**: Tools SHALL return string values (JSON or formatted text) matching the existing pattern in `main.py`
- **REQ-004**: Node type SHALL be validated against the set `{"goal", "task", "subtask"}` on input
- **REQ-005**: All tools SHALL catch exceptions and return error strings starting with "Error:"
- **REQ-006**: Tools SHALL pass `user_id=AGENT_ID` to Mem0 calls (not hardcoded)
- **REQ-007**: Goal node `infer` parameter SHALL default to `False` (raw storage, no LLM extraction for goal text)
- **REQ-008**: `get_goal_tree` SHALL return nested JSON with a `root` node and recursive `children` arrays

### Constraints
- **CON-001**: Python 3.13+ (`pyproject.toml` requires >=3.13)
- **CON-002**: No new dependencies — use `mem0ai` (already in `pyproject.toml`)
- **CON-003**: No hardcoded hostnames, ports, user IDs, or model names
- **CON-004**: No `qdrant_client` or `ollama` direct imports in `main.py`
- **CON-005**: 10GB VRAM limit — goal node operations must not add significant LLM overhead
- **CON-006**: Use `from fastmcp import FastMCP` (not `mcp.server.fastmcp`)
- **CON-007**: Must not break existing `test_main.py` tests

### Guidelines
- **GUD-001**: Parse JSON from Mem0 search results using patterns demonstrated in existing `search_memory` tool
- **GUD-002**: Follow existing `build_search_filters` pattern for goal-specific filter construction
- **GUD-003**: Use Pydantic `BaseModel` for tool input validation (per conventions)
- **GUD-004**: Type hints on ALL function signatures (per conventions)
- **GUD-005**: Mock-friendly design — tool functions should not close over mutable state

## 4. Interfaces & Data Contracts

### 4.1 Metadata Schema for Goal Nodes

All goal nodes stored as Mem0 memories with the following metadata dictionary:

```python
{
    "node_type": str,          # REQUIRED. One of: "goal", "task", "subtask"
    "parent_id": str | None,   # UUID of parent node. None = root goal.
    "root_id": str,            # UUID of absolute top-level goal. Set to own ID if root.
    "session_id": str | None,  # Session identifier for grouping related goals.
    "status": str,             # "active" (default), "completed", "blocked", "abandoned"
    "project_id": str | None,  # Project association (shared with memory tools).
    "tags": list[str]          # Vocabulary tags (shared with memory tools). Default [].
}
```

**Constraints on schema:**
- `node_type` MUST be valid on write (tool validates)
- `root_id` MUST always be set (auto-generated UUID for root goals)
- `parent_id` is null ONLY for root goals
- Mem0 stores metadata as JSON in Qdrant payload; all values must be JSON-serializable
- `tags` field mirrors existing memory tool convention (list of strings)

### 4.2 Tool Interfaces

#### add_goal_node

```
ALGORITHM: add_goal_node
INPUT:
    content (string)                    — Description of the goal/task/subtask
    node_type (string)                  — "goal" | "task" | "subtask"
    parent_id (string, optional)        — UUID of parent node
    root_id (string, optional)          — UUID of root goal (required if parent_id set)
    session_id (string, optional)       — Session grouping key
    status (string, optional)           — Default "active"
    tags (list[string], optional)       — Default []
    project_id (string, optional)       — Project association
    infer (boolean, optional)           — Default False

OUTPUT: string (success message or error)

BEGIN
    // 1. Validate
    IF node_type NOT IN {"goal", "task", "subtask"} THEN
        RETURN "Error: Invalid node_type. Must be goal, task, or subtask."
    END IF

    IF parent_id IS NOT NULL AND root_id IS NULL THEN
        RETURN "Error: root_id is required when parent_id is provided."
    END IF

    // 2. Generate ID
    node_id ← GenerateUUID()

    // 3. Determine root_id
    IF root_id IS NULL THEN
        root_id ← node_id   // This is a root goal
    END IF

    // 4. Build metadata dict (all fields explicit)
    metadata ← {
        "node_type": node_type,
        "parent_id": parent_id,          // None is explicit
        "root_id": root_id,
        "session_id": session_id,        // None is explicit
        "status": status OR "active",
        "project_id": project_id,        // None is explicit
        "tags": tags OR [],
        "validated_at": CurrentTimestampUTC()
    }

    // 5. Store via Mem0
    TRY
        result ← memory_client.add(
            content,
            user_id=AGENT_ID,
            metadata=metadata,
            infer=(infer OR False)
        )
        created_count ← len(result.get("results", []))
        RETURN f"Goal node created. id={node_id}, type={node_type}. Created {created_count} entries."
    CATCH Exception AS e
        RETURN f"Error storing goal node: {str(e)}"
    END TRY
END
```

#### search_goal_nodes

```
ALGORITHM: search_goal_nodes
INPUT:
    query (string)                              — Semantic search query
    node_type (string, optional)                — Filter by "goal", "task", or "subtask"
    root_id (string, optional)                  — Filter by root goal UUID
    parent_id (string, optional)                — Filter by parent UUID
    session_id (string, optional)               — Filter by session
    status (string, optional)                   — Filter by lifecycle status
    project_id (string, optional)               — Filter by project
    tags (list[string], optional)               — Filter by tags (OR logic)
    top_k (integer, optional, default=10)       — Number of results (1-100)
    threshold (float, optional, default=0.1)    — Minimum similarity score (0.0-1.0)

OUTPUT: string (formatted results or "No matching goal nodes found.")

BEGIN
    // 1. Build filter dict
    conditions ← []

    IF node_type IS NOT NULL THEN
        conditions.append({"node_type": {"eq": node_type}})
    END IF

    IF root_id IS NOT NULL THEN
        conditions.append({"root_id": {"eq": root_id}})
    END IF

    IF parent_id IS NOT NULL THEN
        conditions.append({"parent_id": {"eq": parent_id}})
    END IF

    IF session_id IS NOT NULL THEN
        conditions.append({"session_id": {"eq": session_id}})
    END IF

    IF status IS NOT NULL THEN
        conditions.append({"status": {"eq": status}})
    END IF

    IF project_id IS NOT NULL THEN
        conditions.append({"project_id": {"eq": project_id}})
    END IF

    IF tags IS NOT NULL AND len(tags) > 0 THEN
        IF len(tags) == 1 THEN
            conditions.append({"tags": {"contains": tags[0]}})
        ELSE
            tag_conditions ← [{"tags": {"contains": tag}} FOR EACH tag IN tags]
            conditions.append({"OR": tag_conditions})
        END IF
    END IF

    // Compose final filter
    IF len(conditions) == 0 THEN
        filters ← {}
    ELSE IF len(conditions) == 1 THEN
        filters ← conditions[0]
    ELSE
        filters ← {"AND": conditions}
    END IF

    // 2. Search via Mem0
    TRY
        results ← memory_client.search(
            query=query,
            filters=filters,
            user_id=AGENT_ID,
            limit=top_k
        )

        // 3. Threshold filter
        IF threshold > 0 THEN
            results ← [r FOR r IN results IF r.get("score", 0) >= threshold]
        END IF

        IF len(results) == 0 THEN
            RETURN "No matching goal nodes found."
        END IF

        // 4. Format output
        formatted ← "Goal Node Search Results:\n"
        FOR EACH res IN results DO
            node_id ← res.get("id", "unknown")[:8] + "..."
            score ← res.get("score", 0)
            content ← Truncate(res.get("memory", ""), 300)
            meta ← res.get("metadata", {})
            ntype ← meta.get("node_type", "unknown")
            nstatus ← meta.get("status", "N/A")
            nparent ← meta.get("parent_id", "none")[:8] + "..."
            nroot ← meta.get("root_id", "none")[:8] + "..."

            formatted += f"\n[{ntype.upper()}] ID: {node_id} | Status: {nstatus} | Score: {score:.3f}"
            formatted += f"\n  Content: {content}"
            formatted += f"\n  Parent: {nparent} | Root: {nroot}"
        END FOR

        RETURN formatted
    CATCH Exception AS e
        RETURN f"Error searching goal nodes: {str(e)}"
    END TRY
END
```

#### get_goal_tree

```
ALGORITHM: get_goal_tree
INPUT:
    root_id (string)                    — UUID of the root goal to fetch the tree for

OUTPUT: string (JSON tree structure or error)

BEGIN
    TRY
        // 1. Fetch all nodes with this root_id
        //    May need to use search() with high limit if get_all doesn't support
        //    metadata-only filters without entity scope on this Mem0 OSS version.

        filters ← {"root_id": {"eq": root_id}, "node_type": {"in": ["goal", "task", "subtask"]}}

        // Attempt get_all first; fall back to search with broad query if needed
        TRY
            all_nodes ← memory_client.get_all(
                filters=filters,
                user_id=AGENT_ID,
                limit=1000
            )
        CATCH
            // Fallback: search with minimal query to get all nodes
            all_nodes ← memory_client.search(
                query="*",
                filters=filters,
                user_id=AGENT_ID,
                limit=1000
            )
        END TRY

        IF len(all_nodes) == 0 THEN
            RETURN f'{{"error": "No goal tree found for root_id: {root_id}"}}'
        END IF

        // 2. Find root node
        root_node ← NULL
        FOR EACH node IN all_nodes DO
            meta ← node.get("metadata", {})
            IF meta.get("parent_id") IS NULL OR meta.get("node_type") == "goal" AND meta.get("parent_id") IS NULL THEN
                root_node ← node
                BREAK
            END IF
        END FOR

        IF root_node IS NULL THEN
            // No explicit root found; use first goal-type node or first node
            FOR EACH node IN all_nodes DO
                IF node.get("metadata", {}).get("node_type") == "goal" THEN
                    root_node ← node
                    BREAK
                END IF
            END FOR
            IF root_node IS NULL AND len(all_nodes) > 0 THEN
                root_node ← all_nodes[0]
            END IF
        END IF

        // 3. Build tree recursively
        tree ← BuildTreeNode(root_node, all_nodes)

        // 4. Return JSON
        import json
        RETURN json.dumps(tree, indent=2)
    CATCH Exception AS e
        RETURN f"Error building goal tree: {str(e)}"
    END TRY
END

// Helper subroutines

SUBROUTINE: BuildTreeNode
INPUT: node (dict), all_nodes (list[dict])
OUTPUT: dict with tree structure

BEGIN
    node_id ← node.get("id")
    meta ← node.get("metadata", {})

    tree_node ← {
        "id": node_id,
        "content": node.get("memory", ""),
        "type": meta.get("node_type", "unknown"),
        "status": meta.get("status", "active"),
        "tags": meta.get("tags", []),
        "session_id": meta.get("session_id"),
        "project_id": meta.get("project_id"),
        "children": []
    }

    // Find children
    FOR EACH candidate IN all_nodes DO
        IF candidate.get("metadata", {}).get("parent_id") == node_id THEN
            child ← BuildTreeNode(candidate, all_nodes)
            tree_node["children"].append(child)
        END IF
    END FOR

    RETURN tree_node
END
```

#### update_goal_node

```
ALGORITHM: update_goal_node
INPUT:
    node_id (string)                    — UUID of node to update (REQUIRED)
    content (string, optional)          — New content text
    status (string, optional)           — New status
    parent_id (string, optional)        — New parent (for reparenting)
    tags (list[string], optional)       — New tags
    project_id (string, optional)       — New project

OUTPUT: string (success message or error)

BEGIN
    // Validate
    IF status IS NOT NULL AND status NOT IN {"active", "completed", "blocked", "abandoned"} THEN
        RETURN "Error: Invalid status. Must be active, completed, blocked, or abandoned."
    END IF

    // Build metadata update (only include fields that were provided)
    metadata_update ← {}
    IF status IS NOT NULL THEN metadata_update["status"] ← status END IF
    IF parent_id IS NOT NULL THEN metadata_update["parent_id"] ← parent_id END IF
    IF tags IS NOT NULL THEN metadata_update["tags"] ← tags END IF
    IF project_id IS NOT NULL THEN metadata_update["project_id"] ← project_id END IF

    TRY
        memory_client.update(
            node_id,
            text=content,          // None if not provided (Mem0 ignores)
            metadata=metadata_update  // {} if nothing to update (Mem0 ignores)
        )
        RETURN f"Goal node {node_id} updated successfully."
    CATCH Exception AS e
        RETURN f"Error updating goal node: {str(e)}"
    END TRY
END
```

#### delete_goal_node

```
ALGORITHM: delete_goal_node
INPUT:
    node_id (string)                — UUID of node to delete (REQUIRED)

OUTPUT: string (success message or error)

BEGIN
    // No cascade — agent handles child node cleanup separately
    TRY
        memory_client.delete(node_id)
        RETURN f"Goal node {node_id} deleted successfully."
    CATCH Exception AS e
        RETURN f"Error deleting goal node: {str(e)}"
    END TRY
END
```

### 4.3 Helper Functions

#### build_goal_filters (additional to build_search_filters)

```python
# Type signature (Python type hints)
def build_goal_filters(
    node_type: Optional[str],
    root_id: Optional[str],
    parent_id: Optional[str],
    session_id: Optional[str],
    status: Optional[str],
    project_id: Optional[str],
    tags: Optional[List[str]]
) -> Dict[str, Any]:
    """
    Build Mem0-compatible metadata filter dict for goal node search.
    Combines all non-None criteria with AND logic.
    Tags within the list use OR logic (matches existing pattern).
    Returns empty dict if no criteria specified.
    """
```

#### reconstruct_tree (helper for get_goal_tree)

```python
# Type signature
def reconstruct_tree(all_nodes: List[Dict], root_id: str) -> Dict:
    """
    Build a nested tree structure from a flat list of nodes.
    Locates the root node, then recursively attaches children
    where child.metadata.parent_id == parent.id.
    """
```

### 4.4 Pydantic Input Models

Follow existing pattern in `main.py` — one `BaseModel` per tool:

```python
class AddGoalNodeInput(BaseModel):
    content: str = Field(..., description="Description of the goal/task/subtask")
    node_type: str = Field(..., description="One of: goal, task, subtask")
    parent_id: Optional[str] = Field(None, description="UUID of parent node")
    root_id: Optional[str] = Field(None, description="UUID of root goal (required if parent_id set)")
    session_id: Optional[str] = Field(None, description="Session grouping key")
    status: str = Field("active", description="active, completed, blocked, or abandoned")
    tags: List[str] = Field(default_factory=list)
    project_id: Optional[str] = Field(None)
    infer: bool = Field(False, description="Whether to run LLM extraction on content")

class SearchGoalNodesInput(BaseModel):
    query: str = Field(..., description="Natural language search query")
    node_type: Optional[str] = Field(None, description="Filter by goal, task, or subtask")
    root_id: Optional[str] = Field(None)
    parent_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)
    tags: List[str] = Field(default_factory=list)
    top_k: int = Field(10, ge=1, le=100)
    threshold: float = Field(0.1, ge=0.0, le=1.0)

class GetGoalTreeInput(BaseModel):
    root_id: str = Field(..., description="UUID of the root goal")

class UpdateGoalNodeInput(BaseModel):
    node_id: str = Field(..., description="UUID of node to update")
    content: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    parent_id: Optional[str] = Field(None)
    tags: Optional[List[str]] = Field(None)
    project_id: Optional[str] = Field(None)

class DeleteGoalNodeInput(BaseModel):
    node_id: str = Field(..., description="UUID of node to delete")
```

## 5. Acceptance Criteria

- **AC-001**: Given a valid `add_goal_node` call with content "Deploy to staging" and node_type "goal", When the tool executes, Then a Mem0 memory is created with metadata `node_type="goal"`, `root_id` matching the generated UUID, `parent_id=None`, and `status="active"`
- **AC-002**: Given a `root_id` with 3 nodes (1 goal + 2 tasks, one task being child of the goal), When `get_goal_tree(root_id)` is called, Then a nested JSON is returned with the goal as root, the child task nested under it, and the orphan task as a sibling
- **AC-003**: Given `search_goal_nodes(query="deploy", node_type="task")` is called, When a task node exists with content "Deploy to staging", Then that node appears in results with `node_type == "task"` and ID displayed in format `xxxx-...`
- **AC-004**: Given an empty goals collection, When `search_goal_nodes(query="anything")` is called, Then "No matching goal nodes found." is returned
- **AC-005**: Given a valid `update_goal_node(node_id, status="completed")` call, When executed, Then `memory_client.update()` is called with that node_id and metadata containing only `{"status": "completed"}`
- **AC-006**: Given a valid `delete_goal_node(node_id)` call, When executed, Then `memory_client.delete()` is called with that node_id
- **AC-007**: Given any tool call that causes a `memory_client` exception, Then the return value starts with "Error:" and contains the exception message
- **AC-008**: Given the proxy is started with updated config, When `get_allowed_services("agent_alpha")` is called, Then `memory__search_goal_nodes` and `memory__get_goal_tree` appear in allowed_tools
- **AC-009**: Given the proxy is started with updated config, When `get_allowed_services("agent_admin")` is called, Then all 5 new goal-tree tools appear alongside existing memory tools
- **AC-010**: All existing tests in `test_main.py` pass after integration

## 6. Test Automation Strategy

- **Test Levels**: Unit tests (mocked memory_client)
- **Frameworks**: pytest (already configured in `pyproject.toml`)
- **Test Pattern**: Follow existing `test_main.py` patterns:
  - Mock `memory_client` globally via `MagicMock`
  - Each test class corresponds to one tool
  - Reset mocks between tests
  - Verify call arguments, return value format, error handling
- **New Test Classes** (in `test_main.py`):
  - `TestAddGoalNode`: validation, metadata construction, error handling
  - `TestSearchGoalNodes`: filter building, result formatting, empty results
  - `TestGetGoalTree`: tree reconstruction, missing root, flat results
  - `TestUpdateGoalNode`: partial updates, status validation
  - `TestDeleteGoalNode`: deletion call, error handling
- **Coverage**: All new functions, all filter combinations, all error paths
- **No new dependencies**: `pytest` and `pytest-asyncio` already in `pyproject.toml`

## 7. Rationale & Context

**Why Mem0 instead of raw Qdrant?**
- `main.py` already uses Mem0; goal_trees.py duplicates Qdrant/Ollama connection logic
- Single `memory_client` = single config, single connection pool, consistent error handling
- Mem0's metadata filtering provides equivalent functionality to Qdrant payload filtering
- Fewer dependencies to maintain (no direct `qdrant_client` or `ollama` packages)

**Why a single collection?**
- Mem0 manages collection lifecycle; creating per-session collections fights the framework
- `session_id` metadata field provides session-level partitioning without collection overhead
- Simpler mental model: all memories (general + goal nodes) are in one place, queryable with filters

**Why `infer=False` for goal nodes?**
- Goal/task text is structured by the calling agent; LLM extraction would be redundant
- Reduces LLM load (important given 10GB VRAM limit and already-loaded llama3.1 model)

**Why flat storage + in-memory tree build?**
- Mem0 has no graph traversal or relationship query API
- Goal trees are expected to be small (tens to hundreds of nodes per root)
- Fetch-all-by-root_id + client-side tree build is simple, correct, and fast enough

## 8. Dependencies & External Integrations

### External Systems
- **EXT-001**: Qdrant (at QDRANT_HOST:6333) — accessed via Mem0, not directly
- **EXT-002**: Ollama (at OLLAMA_URL) — accessed via Mem0 for embeddings, not directly

### Infrastructure Dependencies
- **INF-001**: `memory_client` (Mem0 OSS `Memory` instance) — must be initialized before tool calls
- **INF-002**: Environment variables: `AGENT_ID`, `QDRANT_HOST`, `QDRANT_PORT`, `OLLAMA_URL`, `EMBEDDING_MODEL`, `LLM_MODEL`

### Technology Platform Dependencies
- **PLT-001**: `mem0ai` package (already in `pyproject.toml`) — provides `Memory` class
- **PLT-002**: `fastmcp>=3.2.4` — provides `@mcp.tool()` decorator and server runtime
- **PLT-003**: `pydantic>=2.10.6` — input model validation
- **PLT-004**: `pyyaml>=6.0.2` — existing dep for sync_metadata; not needed for goal tools
- **PLT-005**: `python-dotenv>=1.2.2` — environment variable loading

## 9. Examples & Edge Cases

### Root goal creation
```
Input: add_goal_node(content="Ship v2.0", node_type="goal")
Result: node_id and root_id are the same UUID, parent_id is None, status is "active"
```

### Child task creation
```
Input: add_goal_node(content="Write tests", node_type="task", parent_id="<goal-uuid>", root_id="<goal-uuid>")
Result: parent_id and root_id point to existing nodes, node_type is "task"
```

### Nested tree output (get_goal_tree)
```json
{
  "id": "abc123...",
  "content": "Ship v2.0",
  "type": "goal",
  "status": "active",
  "tags": [],
  "session_id": "session-1",
  "project_id": null,
  "children": [
    {
      "id": "def456...",
      "content": "Write tests",
      "type": "task",
      "status": "active",
      "tags": ["testing"],
      "session_id": "session-1",
      "project_id": null,
      "children": []
    }
  ]
}
```

### Edge cases to handle
- Empty content string — Mem0 will handle (embedding of empty text fails gracefully)
- Invalid node_type — validated against enum, returns error message
- parent_id without root_id — validation rejects, returns error message
- root_id that doesn't exist — get_goal_tree returns empty tree
- Duplicate content with different node_types — both stored (no dedup — goal-keeper agent handles later)
- Very deep trees (10+ levels) — recursion depth in BuildTreeNode; use iterative approach if needed
- Concurrent modifications — not handled (single-user system per constraints)

## 10. Validation Criteria

- **VAL-001**: `src/goal_trees.py` is deleted and no imports reference it
- **VAL-002**: All `from fastmcp import FastMCP` imports are consistent
- **VAL-003**: No `qdrant_client` or `ollama` imports in `main.py`
- **VAL-004**: `memory_client` is the sole interface to Qdrant/Ollama for all tools
- **VAL-005**: `mcp-proxy-server.py` reads port from env var, not hardcoded 8001
- **VAL-006**: `.env` has no shell variable interpolation
- **VAL-007**: `pytest src/test_main.py` passes with zero failures
- **VAL-008**: All 10 tools appear in proxy tool listing

## 11. Related Specifications / Further Reading
- Mem0 OSS Python client: `.agents/skills/mem0/client/python.md`
- Mem0 API filter system: `.agents/skills/mem0/references/api-reference.md`
- Current main.py: `src/main.py`
- Current test patterns: `src/test_main.py`
- Project conventions: `docs/context/conventions.md`
- Project constraints: `docs/context/constraints.md`