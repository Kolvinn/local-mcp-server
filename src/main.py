"""MCP Memory Server v0 - Mem0-backed memory layer for AI agents."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# =====================================================================
# 1. ENVIRONMENT CONFIGURATION
# =====================================================================

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
AGENT_ID = os.getenv("AGENT_ID", "default_agent")
STALENESS_WINDOW_DAYS = int(os.getenv("STALENESS_WINDOW_DAYS", "30"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
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

    try:
        from mem0 import Memory
    except ImportError:
        # For testing environments where mem0 isn't installed
        raise ImportError("mem0 is required but not installed")

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
                "base_url": OLLAMA_URL
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBEDDING_MODEL,
                "base_url": OLLAMA_URL
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


# =====================================================================
# 5. FILTER CONSTRUCTION HELPER
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
    source_path: Optional[str] = None
) -> str:
    """Store a new memory with metadata.

    Args:
        content: The memory content to store
        tags: Vocabulary tags for filtering
        project_id: Project identifier
        source_user: Who this memory is about
        related_files: Files associated with this memory (list of {path, entered})
        source_path: Directory context at creation
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
            infer=True
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
# 7. SERVER ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=HOST, port=PORT)
