"""MCP Memory Server v0 - Mem0-backed memory layer for AI agents."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from mem0 import Memory
# Load environment variables
load_dotenv()

# =====================================================================
# 1. ENVIRONMENT CONFIGURATION
# =====================================================================

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
AGENT_ID = os.getenv("AGENT_ID", "default_agent")
STALENESS_WINDOW_DAYS = int(os.getenv("STALENESS_WINDOW_DAYS", "30"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_MEM0_PORT", "8001"))
MEMORY_CONTEXT_BASE = Path(os.getenv("MEMORY_CONTEXT_BASE", "/home/dev/app")).resolve()

# =====================================================================
# 2. FASTMCP INSTANCE CREATION
# =====================================================================

mcp = FastMCP("memory-server")

# =====================================================================
# 3. MEM0 INITIALIZATION (Fail-Fast)
# =====================================================================

# Global memory_client - initialized below but can be mocked for testing
memory_client = None


def init_memory_client():
    """Initialize the Mem0 memory client. Can be mocked for testing."""
    global memory_client

    if memory_client is not None:
        return memory_client

    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": QDRANT_HOST,
                "port": QDRANT_PORT,
            }
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": LLM_MODEL,
                "ollama_base_url": OLLAMA_URL
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBEDDING_MODEL,
                "ollama_base_url": OLLAMA_URL
            }
        }
    }

    # Fail-fast: server won't start if Qdrant/Ollama unreachable
    try:
        memory_client = Memory.from_config(config)
    except Exception as e:
        print(f"FATAL: Failed to initialize Mem0: {e}")
        raise

    return memory_client


# Initialize on import (can be overridden by tests)
init_memory_client()

# =====================================================================
# 4. PYDANTIC MODELS
# =====================================================================


class AddMemoryInput(BaseModel):
    content: str = Field(..., description="The memory content to store")
    tags: List[str] = Field(default_factory=list, description="Vocabulary tags for filtering")
    project_id: Optional[str] = Field(None, description="Project identifier")
    source_user: Optional[str] = Field(None, description="Who this memory is about")
    related_files: List[Dict[str, str]] = Field(default_factory=list, description="Files associated with this memory (list of {path, entered})")
    source_path: Optional[str] = Field(None, description="Directory context at creation")


class SearchMemoryInput(BaseModel):
    query: str = Field(..., description="Natural language search query")
    tags: List[str] = Field(default_factory=list, description="Filter by tags (OR logic within list)")
    project_id: Optional[str] = Field(None, description="Filter by project")
    source_user: Optional[str] = Field(None, description="Filter by who the memory is about")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")
    threshold: float = Field(0.1, ge=0.0, le=1.0, description="Minimum similarity score")


class DeleteMemoryInput(BaseModel):
    memory_id: str = Field(..., description="UUID of the memory to delete")


class SyncMetadataInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to create/update .memory-context.yaml")
    project_id: str = Field(..., description="Project identifier to write")
    tags: List[str] = Field(default_factory=list, description="Default tags for this project")
    scope_summary: Optional[str] = Field(None, description="Human-readable project summary")


class ListProjectsInput(BaseModel):
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of projects to return")


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


# =====================================================================
# 5. FILTER CONSTRUCTION HELPERS
# =====================================================================


def build_search_filters(
    tags: List[str],
    project_id: Optional[str],
    source_user: Optional[str]
) -> Dict[str, Any]:
    """Build search filters for Mem0 based on provided criteria."""
    conditions = []

    if tags:
        if len(tags) == 1:
            conditions.append({"tags": {"contains": tags[0]}})
        else:
            tag_conditions = [{"tags": {"contains": tag}} for tag in tags]
            conditions.append({"OR": tag_conditions})

    if project_id:
        conditions.append({"project_id": project_id})

    if source_user:
        conditions.append({"source_user": source_user})

    if len(conditions) == 0:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"AND": conditions}


def build_goal_filters(
    node_type: Optional[str],
    root_id: Optional[str],
    parent_id: Optional[str],
    session_id: Optional[str],
    status: Optional[str],
    project_id: Optional[str],
    tags: Optional[List[str]],
) -> Dict[str, Any]:
    """Build Mem0-compatible metadata filter dict for goal node search.

    Combines all non-None criteria with AND logic.
    Tags within the list use OR logic (matches existing pattern).
    Returns empty dict if no criteria specified.
    """
    conditions: List[Dict[str, Any]] = []

    if node_type is not None:
        conditions.append({"node_type": {"eq": node_type}})

    if root_id is not None:
        conditions.append({"root_id": {"eq": root_id}})

    if parent_id is not None:
        conditions.append({"parent_id": {"eq": parent_id}})

    if session_id is not None:
        conditions.append({"session_id": {"eq": session_id}})

    if status is not None:
        conditions.append({"status": {"eq": status}})

    if project_id is not None:
        conditions.append({"project_id": {"eq": project_id}})

    if tags is not None and len(tags) > 0:
        if len(tags) == 1:
            conditions.append({"tags": {"contains": tags[0]}})
        else:
            tag_conditions = [{"tags": {"contains": tag}} for tag in tags]
            conditions.append({"OR": tag_conditions})

    if len(conditions) == 0:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"AND": conditions}


def reconstruct_tree(all_nodes: List[Dict], root_id: str) -> Dict:
    """Build a nested tree structure from a flat list of nodes.

    Locates the root node by matching root_id in metadata, then recursively
    attaches children where child.metadata.parent_id == parent.id.
    Returns empty dict if no root node can be identified.
    """
    if not all_nodes:
        return {}

    # Priority 1: node with parent_id=None and matching root_id
    root_node = None
    for node in all_nodes:
        meta = node.get("metadata", {})
        if meta.get("root_id") == root_id and meta.get("parent_id") is None:
            root_node = node
            break

    # Priority 2: first goal-type node with matching root_id
    if root_node is None:
        for node in all_nodes:
            meta = node.get("metadata", {})
            if meta.get("root_id") == root_id and meta.get("node_type") == "goal":
                root_node = node
                break

    # Priority 3: first node with matching root_id
    if root_node is None:
        for node in all_nodes:
            if node.get("metadata", {}).get("root_id") == root_id:
                root_node = node
                break

    if root_node is None:
        return {}

    def _build_tree_node(node: Dict, nodes: List[Dict]) -> Dict:
        """Recursively build a tree node and its children."""
        node_id = node.get("id")
        meta = node.get("metadata", {})

        tree_node: Dict[str, Any] = {
            "id": node_id,
            "content": node.get("memory", ""),
            "type": meta.get("node_type", "unknown"),
            "status": meta.get("status", "active"),
            "tags": meta.get("tags", []),
            "session_id": meta.get("session_id"),
            "project_id": meta.get("project_id"),
            "children": [],
        }

        for candidate in nodes:
            if candidate.get("metadata", {}).get("parent_id") == node_id:
                child = _build_tree_node(candidate, nodes)
                tree_node["children"].append(child)

        return tree_node

    return _build_tree_node(root_node, all_nodes)


# =====================================================================
# 6. TOOL IMPLEMENTATIONS
# =====================================================================


@mcp.tool()
def add_memory(
    content: str,
    tags: List[str] = None,
    project_id: Optional[str] = None,
    source_user: Optional[str] = None,
    related_files: List[Dict[str, str]] = None,
    source_path: Optional[str] = None,
    infer: bool = True
) -> str:
    """Store a new memory with metadata.

    Args:
        content: The memory content to store
        tags: Vocabulary tags for filtering
        project_id: Project identifier
        source_user: Who this memory is about
        related_files: Files associated with this memory (list of {path, entered})
        source_path: Directory context at creation
        infer: Whether to infer additional metadata from content (default: True)
    """
    try:
        # Build metadata dict with all fields (None values are explicit, not omitted)
        metadata: Dict[str, Any] = {
            "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tags": tags or [],
            "project_id": project_id,  # None is fine - explicit absence
            "source_user": source_user,  # None is fine - explicit absence
            "related_files": related_files or [],
            "source_path": source_path,  # None is fine - explicit absence
        }

        result = memory_client.add(
            content,
            user_id=AGENT_ID,
            metadata=metadata,
            infer=infer
        )

        # Count created/updated entries
        created_count = len(result.get("results", []))
        return f"Memory stored successfully. Created/updated {created_count} entries."

    except Exception as e:
        return f"Error storing memory: {str(e)}"


@mcp.tool()
def search_memory(
    query: str,
    tags: List[str] = None,
    project_id: Optional[str] = None,
    source_user: Optional[str] = None,
    top_k: int = 10,
    threshold: float = 0.1
) -> str:
    """Search memories using natural language query.

    Args:
        query: Natural language search query
        tags: Filter by tags (OR logic within list)
        project_id: Filter by project
        source_user: Filter by who the memory is about
        top_k: Number of results (1-100)
        threshold: Minimum similarity score (0.0-1.0)
    """
    try:
        # Build filters
        filters = build_search_filters(tags or [], project_id, source_user)

        # Search memories
        results = memory_client.search(
            query=query,
            filters=filters,
            user_id=AGENT_ID,
            limit=top_k
        )

        # Filter by threshold manually if needed (Mem0 may not support threshold directly)
        if threshold > 0:
            results = [r for r in results if r.get("score", 0) >= threshold]

        if not results:
            return "No relevant memories found."

        # Format results
        formatted = "Retrieved Memories:\n"
        for res in results:
            memory_id = res.get("id", "unknown")[:8] + "..."  # Truncated ID
            score = res.get("score", 0)
            memory_text = res.get("memory", "")
            if len(memory_text) > 200:
                memory_text = memory_text[:200] + "..."

            metadata = res.get("metadata", {})
            project = metadata.get("project_id", "N/A")
            res_tags = metadata.get("tags", [])

            formatted += f"\n[ID: {memory_id}] Score: {score:.3f}\n"
            formatted += f"  Content: {memory_text}\n"
            formatted += f"  Project: {project} | Tags: {', '.join(res_tags) if res_tags else 'none'}\n"

        return formatted

    except Exception as e:
        return f"Error searching memories: {str(e)}"


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Delete a specific memory by ID.

    Args:
        memory_id: UUID of the memory to delete
    """
    try:
        memory_client.delete(memory_id)
        return f"Memory {memory_id} successfully deleted."
    except Exception as e:
        return f"Error deleting memory: {str(e)}"


@mcp.tool()
def sync_metadata(
    file_path: str,
    project_id: str,
    tags: List[str] = None,
    scope_summary: Optional[str] = None
) -> str:
    """Create or update a .memory-context.yaml file.

    Args:
        file_path: Absolute path to create/update .memory-context.yaml
        project_id: Project identifier to write
        tags: Default tags for this project
        scope_summary: Human-readable project summary
    """
    try:
        # Validate file path for security
        resolved = Path(file_path).resolve()

        # Must end with .memory-context.yaml
        if resolved.name != ".memory-context.yaml":
            return "Error: file_path must point to a .memory-context.yaml file"

        # Must be within allowed base directory
        if not str(resolved).startswith(str(MEMORY_CONTEXT_BASE)):
            return f"Error: file_path must be within {MEMORY_CONTEXT_BASE}"
        # Build YAML content
        yaml_data = {
            "version": 1,
            "project_id": project_id,
            "tags": tags or [],
        }

        if scope_summary:
            yaml_data["scope_summary"] = scope_summary

        # Create parent directory if needed
        parent_dir = resolved.parent
        if parent_dir and not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        with open(resolved, "w", encoding="utf-8") as f:
            yaml.dump(
                yaml_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True
            )

        return f"Metadata synchronized to {resolved}"

    except Exception as e:
        return f"Error synchronizing metadata: {str(e)}"


@mcp.tool()
def list_projects(limit: int = 100) -> str:
    """List all unique project IDs from stored memories.

    Args:
        limit: Maximum number of memories to scan (1-1000)
    """
    try:
        # Get all memories for this user
        # Note: Mem0's get_all method may vary; using search with broad query as fallback
        try:
            all_memories = memory_client.get_all(user_id=AGENT_ID, filters={}, limit=limit)
        except AttributeError:
            # Fallback: use search with empty/broad query
            all_memories = memory_client.search(
                query="*",
                filters={},
                user_id=AGENT_ID,
                limit=limit
            )

        # Extract unique project_ids from metadata
        project_ids = set()
        for memory in all_memories:
            metadata = memory.get("metadata", {})
            project_id = metadata.get("project_id")
            if project_id:
                project_ids.add(project_id)

        if not project_ids:
            return "No projects found."

        # Return sorted list
        sorted_projects = sorted(project_ids)
        return "Projects:\n" + "\n".join(f"  - {pid}" for pid in sorted_projects)

    except Exception as e:
        return f"Error listing projects: {str(e)}"


# =====================================================================
# 7. GOAL-TREE TOOL IMPLEMENTATIONS
# =====================================================================


@mcp.tool()
def add_goal_node(input: AddGoalNodeInput) -> str:
    """Create a new goal/task/subtask node in the goal tree.

    Args:
        input: AddGoalNodeInput with content, node_type, parent_id, root_id,
               session_id, status, tags, project_id, and infer flags.
    """
    # Validate node_type
    valid_types = {"goal", "task", "subtask"}
    if input.node_type not in valid_types:
        return "Error: Invalid node_type. Must be goal, task, or subtask."

    # Validate parent_id requires root_id
    if input.parent_id is not None and input.root_id is None:
        return "Error: root_id is required when parent_id is provided."

    # Generate node ID
    node_id = str(uuid.uuid4())

    # Determine root_id (self-root if not provided)
    root_id = input.root_id if input.root_id is not None else node_id

    # Build metadata dict with all fields (None values are explicit, not omitted)
    metadata: Dict[str, Any] = {
        "node_type": input.node_type,
        "parent_id": input.parent_id,
        "root_id": root_id,
        "session_id": input.session_id,
        "status": input.status or "active",
        "project_id": input.project_id,
        "tags": input.tags or [],
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        result = memory_client.add(
            input.content,
            user_id=AGENT_ID,
            metadata=metadata,
            infer=input.infer or False,
        )

        created_count = len(result.get("results", []))
        return (
            f"Goal node created. id={node_id}, type={input.node_type}. "
            f"Created {created_count} entries."
        )

    except Exception as e:
        return f"Error storing goal node: {str(e)}"


@mcp.tool()
def search_goal_nodes(input: SearchGoalNodesInput) -> str:
    """Search goal nodes using semantic search with metadata filters.

    Args:
        input: SearchGoalNodesInput with query, optional metadata filters,
               top_k result count, and similarity threshold.
    """
    try:
        # Build filters using the helper
        filters = build_goal_filters(
            node_type=input.node_type,
            root_id=input.root_id,
            parent_id=input.parent_id,
            session_id=input.session_id,
            status=input.status,
            project_id=input.project_id,
            tags=input.tags if input.tags else None,
        )

        # Search via Mem0
        results = memory_client.search(
            query=input.query,
            filters=filters,
            user_id=AGENT_ID,
            limit=input.top_k,
        )

        # Filter by threshold manually if needed
        if input.threshold > 0:
            results = [r for r in results if r.get("score", 0) >= input.threshold]

        if not results:
            return "No matching goal nodes found."

        # Format results
        formatted = "Goal Node Search Results:\n"
        for res in results:
            node_id = res.get("id", "unknown")[:8] + "..."
            score = res.get("score", 0)
            content = res.get("memory", "")
            if len(content) > 300:
                content = content[:300] + "..."

            meta = res.get("metadata", {})
            ntype = meta.get("node_type", "unknown")
            nstatus = meta.get("status", "N/A")

            parent_raw = meta.get("parent_id")
            nparent = (parent_raw[:8] + "...") if parent_raw else "none"

            root_raw = meta.get("root_id")
            nroot = (root_raw[:8] + "...") if root_raw else "none"

            formatted += (
                f"\n[{ntype.upper()}] ID: {node_id} | Status: {nstatus} "
                f"| Score: {score:.3f}"
            )
            formatted += f"\n  Content: {content}"
            formatted += f"\n  Parent: {nparent} | Root: {nroot}"

        return formatted

    except Exception as e:
        return f"Error searching goal nodes: {str(e)}"


@mcp.tool()
def get_goal_tree(input: GetGoalTreeInput) -> str:
    """Fetch the entire goal tree for a given root_id as nested JSON.

    Retrieves all nodes sharing the same root_id, then reconstructs the
    hierarchical tree structure with a root node and recursive children arrays.

    Args:
        input: GetGoalTreeInput with the root_id of the goal tree.
    """
    try:
        # Build filters to fetch all nodes belonging to this tree
        filters: Dict[str, Any] = {
            "root_id": {"eq": input.root_id},
            "node_type": {"in": ["goal", "task", "subtask"]},
        }

        # Attempt get_all first; fall back to search with broad query
        try:
            all_nodes = memory_client.get_all(
                filters=filters,
                user_id=AGENT_ID,
                limit=1000,
            )
        except Exception:
            all_nodes = memory_client.search(
                query="*",
                filters=filters,
                user_id=AGENT_ID,
                limit=1000,
            )

        if not all_nodes:
            return json.dumps(
                {"error": f"No goal tree found for root_id: {input.root_id}"}
            )

        # Reconstruct tree from flat results
        tree = reconstruct_tree(all_nodes, input.root_id)

        if not tree:
            return json.dumps(
                {"error": f"No goal tree found for root_id: {input.root_id}"}
            )

        return json.dumps(tree, indent=2)

    except Exception as e:
        return f"Error building goal tree: {str(e)}"


@mcp.tool()
def update_goal_node(input: UpdateGoalNodeInput) -> str:
    """Update an existing goal node's content, status, parent_id, tags, or project_id.

    Only the fields that are explicitly provided will be updated.
    Set status to one of: active, completed, blocked, abandoned.

    Args:
        input: UpdateGoalNodeInput with node_id and optional fields to update.
    """
    # Validate status if provided
    valid_statuses = {"active", "completed", "blocked", "abandoned"}
    if input.status is not None and input.status not in valid_statuses:
        return (
            "Error: Invalid status. Must be active, completed, "
            "blocked, or abandoned."
        )

    # Build metadata update with only provided fields
    metadata_update: Dict[str, Any] = {}
    if input.status is not None:
        metadata_update["status"] = input.status
    if input.parent_id is not None:
        metadata_update["parent_id"] = input.parent_id
    if input.tags is not None:
        metadata_update["tags"] = input.tags
    if input.project_id is not None:
        metadata_update["project_id"] = input.project_id

    try:
        memory_client.update(
            input.node_id,
            data=input.content,
            metadata=metadata_update,
        )
        return f"Goal node {input.node_id} updated successfully."

    except Exception as e:
        return f"Error updating goal node: {str(e)}"


@mcp.tool()
def delete_goal_node(input: DeleteGoalNodeInput) -> str:
    """Delete a single goal node by ID. Does NOT cascade to children.

    Agent is responsible for handling child node cleanup separately.

    Args:
        input: DeleteGoalNodeInput with the node_id to delete.
    """
    try:
        memory_client.delete(input.node_id)
        return f"Goal node {input.node_id} deleted successfully."

    except Exception as e:
        return f"Error deleting goal node: {str(e)}"


# =====================================================================
# 8. SERVER ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    mcp.run()
