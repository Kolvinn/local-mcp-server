from fastmcp import FastMCP
from fastmcp.server import create_proxy
import os
import os
import json
import httpx
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from mem0 import Memory
from pydantic import BaseModel
# 1. Initialize the central orchestrator






# =====================================================================
# 1. SERVER & MEM0 INITIALIZATION
# =====================================================================

# Initialize the MCP Server
mcp = FastMCP("LocalAI-Memory-Layer")

# Configure Mem0 to use your local Qdrant container and Ollama embeddings
# Update these environment variables in your docker-compose.yml
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3") # or mxbai-embed-large

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
            "model": "llama3.1:8b", # Used for Mem0's internal fact extraction
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

# Initialize the Mem0 client
memory_client = Memory.from_config(config)

# =====================================================================
# 2. HELPER FUNCTIONS (The "Generic Fill-Ins")
# =====================================================================

async def ask_local_llm(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """
    Generic helper to query your local LLM (via LiteLLM proxy or Ollama directly)
    for reasoning tasks like context drift detection.
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": "llama3.1:8b", # CHANGE THIS to your preferred reasoning model
        "prompt": f"System: {system_prompt}\n\nUser: {prompt}",
        "stream": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error contacting local LLM: {str(e)}"

# =====================================================================
# 3. MCP TOOL ENDPOINTS
# =====================================================================

@mcp.tool()
async def search_project_memory(query: str, project_id: str, active_collections: List[str]) -> str:
    """
    Retrieves long-term architectural rules and facts from Qdrant.
    
    Args:
        query: The specific question or topic (e.g., "How is Traefik configured?")
        project_id: The identifier for the current project.
        active_collections: A list of tags from the manifest to filter results (e.g., ["infrastructure"]).
    """
    # Build the metadata filter strictly based on the manifest state
    filters = {
        "AND": [
            {"project_id": project_id},
            {"collection": {"in": active_collections}}
        ]
    }
    
    try:
        # Mem0 search semantic retrieval
        results = memory_client.search(query=query, user_id="roo_agent", filters=filters)
        
        if not results:
            return "No relevant memories found in the current context."
            
        # Format the output for Roo Code
        formatted_results = "Retrieved Context:\n"
        for res in results:
            formatted_results += f"- {res['memory']} (Score: {res['score']})\n"
            
        return formatted_results
    except Exception as e:
        return f"Error retrieving memory: {str(e)}"


@mcp.tool()
async def detect_context_drift(current_task: str, chat_history_preview: str, manifest_summary: str) -> str:
    """
    Compares the current task against the established project state to warn the user if context is shifting.
    
    Args:
        current_task: What Roo Code is currently trying to accomplish.
        chat_history_preview: The last few messages to establish intent.
        manifest_summary: The 'state_summary' from memory-context.json.
    """
    system_prompt = (
        "You are an architectural state monitor. Your job is to compare the "
        "User's Current Task against the Established Project Summary. "
        "Respond ONLY with a JSON object containing 'drift_detected' (boolean) "
        "and 'analysis' (string explaining why)."
    )
    
    user_prompt = (
        f"Established Summary: {manifest_summary}\n"
        f"Current Task: {current_task}\n"
        f"Recent Chat: {chat_history_preview}"
    )
    
    # LLM processes the drift detection
    analysis_json_str = await ask_local_llm(user_prompt, system_prompt)
    
    return f"Context Alignment Check Result:\n{analysis_json_str}"


@mcp.tool()
async def compact_and_promote(session_transcript: str, project_id: str, active_collections: List[str]) -> str:
    """
    Summarizes the current session into permanent facts and saves them to Qdrant via Mem0.
    
    Args:
        session_transcript: A summary of the rules, code changes, or decisions made in this session.
        project_id: The identifier for the current project.
        active_collections: Tags to attach to this memory (e.g., ["docker", "api"]).
    """
    # In a production environment, you might want to use the LLM helper here 
    # to extract "invariants" before passing to Mem0, but Mem0 handles a lot of this natively.
    
    metadata = {
        "project_id": project_id,
        "collection": active_collections[0] if active_collections else "general"
    }
    
    try:
        # infer=True allows Mem0 to update existing facts rather than duplicating them
        memory_client.add(
            session_transcript, 
            user_id="roo_agent", 
            metadata=metadata, 
            infer=True 
        )
        return f"Successfully compacted and promoted memory to Qdrant for project '{project_id}'."
    except Exception as e:
        return f"Failed to promote memory: {str(e)}"


@mcp.tool()
async def sync_manifest_state(manifest_path: str, new_state_summary: str, new_collections: List[str]) -> str:
    """
    Updates the local memory-context.json file to reflect the new state of the project.
    
    Args:
        manifest_path: The absolute or relative path to memory-context.json in the docker container.
        new_state_summary: The updated high-level summary of the project state.
        new_collections: The updated list of active tags.
    """
    # IMPORTANT: For this to work, the directory containing memory-context.json 
    # MUST be mounted as a volume in your docker-compose.yml for this service.
    
    if not os.path.exists(manifest_path):
        return f"Error: Manifest file not found at {manifest_path}. Ensure Docker volumes are mounted correctly."
        
    try:
        with open(manifest_path, 'r') as f:
            current_state = json.load(f)
            
        current_state['state_summary'] = new_state_summary
        current_state['active_collections'] = new_collections
        
        with open(manifest_path, 'w') as f:
            json.dump(current_state, f, indent=4)
            
        return "Manifest state synchronized successfully."
    except Exception as e:
        return f"Failed to sync manifest: {str(e)}"


@mcp.tool()
async def forget_specific_fact(memory_id: str) -> str:
    """
    Deletes a specific memory from Qdrant if it is hallucinated or permanently outdated.
    
    Args:
        memory_id: The specific UUID of the memory to delete (obtained via search).
    """
    try:
        memory_client.delete(memory_id)
        return f"Memory {memory_id} successfully purged from the database."
    except Exception as e:
        return f"Failed to delete memory: {str(e)}"


if __name__ == "__main__":
    # IMPORTANT: Use transport="sse" or "streamable-http" for network access
    # Use host="0.0.0.0" to allow connections from outside the container
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
