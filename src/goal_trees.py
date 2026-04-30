import uuid
import requests
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.http import models
import os
import ollama
from qdrant_client.http.exceptions import UnexpectedResponse

# Initialize FastMCP server
# FastMCP defaults to stdio, which is ideal for an overriding proxy executing this script.
mcp = FastMCP("Goal-Tree-Manager")
QdrantClient.set_model
# Backend Resource Configurations
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
OLLAMA_URL =os.getenv("OLLAMA_URL", "http://ollama:11434/api/embeddings")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")
VECTOR_SIZE = 768


q_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

o_client = ollama.Client(host="http://ollama:11434")

def get_embedding(text: str) -> List[float]:
    """Helper function to fetch embeddings from local Ollama container."""
    if not text.strip():
        raise ValueError("Cannot embed empty text.")
    
    try:
        # response = requests.post(
        #     OLLAMA_URL, 
        #     json={"model": OLLAMA_MODEL, "prompt": text},
        #     timeout=10
        # )
        response = o_client.embeddings(model=OLLAMA_MODEL, prompt=text)
        #response.raise_for_status()
        return response["embedding"]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to connect to Ollama: {str(e)}")

@mcp.tool()
def create_session_collection(session_id: str) -> str:
    """
    CRITICAL FIRST STEP: Run this before any other tool to initialize the session.
    Creates an isolated Qdrant vector database collection for the current session.
    
    Args:
        session_id: A unique string identifier for the current session (e.g., 'session_123').
        
    Returns:
        A success message containing the exact collection_name you must use for subsequent steps.
    """
    collection_name = f"session_{session_id.replace('-', '_')}"
    
    # nomic-embed-text outputs 768 dimensions by default
    vector_size = 768 
    
    try:
        q_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size, 
                distance=models.Distance.COSINE
            )
        )
        
        q_client.create_payload_index(
            collection_name=collection_name,
            field_name="type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        return f"SUCCESS: Collection '{collection_name}' is ready. Use this name for all ingestion and search tasks."
    except Exception as e:
        return f"ERROR: Failed to create collection. Details: {str(e)}"

@mcp.tool()
def ingest_node(
    collection_name: str, 
    text: str, 
    node_type: str, 
    parent_id: Optional[str] = None, 
    root_id: Optional[str] = None
) -> str:
    """
    Adds a new goal, task, or subtask into the tree structure.
    
    Args:
        collection_name: The name returned by create_session_collection.
        text: The specific description of the objective or task.
        node_type: STRICTLY use 'goal', 'task', or 'subtask'.
        parent_id: UUID of the direct parent. Omit if this is a top-level goal.
        root_id: UUID of the absolute top-level goal. Omit if this is a top-level goal.
        
    Returns:
        A JSON string containing the generated 'id' of the new node.
    """
    valid_types = ['goal', 'task', 'subtask']
    if node_type not in valid_types:
        return f"ERROR: Invalid node_type. Must be one of {valid_types}."

    try:
        node_id = str(uuid.uuid4())
        vector = get_embedding(text)
        
        payload = {
            "content": text,
            "type": node_type,
            "parent_id": parent_id,
            "root_id": root_id or node_id
        }

        q_client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(id=node_id, vector=vector, payload=payload)]
        )
        
        return f'{{"status": "success", "id": "{node_id}", "type": "{node_type}"}}'
    except Exception as e:
        return f"ERROR: Ingestion failed. Details: {str(e)}"

@mcp.tool()
def search_similar_nodes(
    collection_name: str, 
    text: str, 
    target_type: Optional[str] = None, 
    limit: int = 3
) -> str:
    """
    Analyzes semantic similarity to detect redundancy or verify goal alignment.
    Use this BEFORE creating a new task to ensure it doesn't already exist, or to 
    find which goal a new task belongs to.
    
    Args:
        collection_name: The target session collection.
        text: The query text to compare against the database.
        target_type: Optional. Filter results by node type (e.g., 'goal' to only check against goals).
        limit: Number of results to return (default 3).
        
    Returns:
        A JSON string list of similar nodes with their similarity scores (0.0 to 1.0).
    """
    try:
        #query_vector = get_embedding(text)
        
        query_filter = None
        if target_type:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="type", match=models.MatchValue(value=target_type))]
            )
        QdrantClient.Mode.QueryRequest
        results = q_client.query(
            collection_name=collection_name,
            query_text=text,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )
        
        if not results:
            return "[] (No similar nodes found)"

        formatted_results = [
            {
                "id": res.id, 
                "score": round(res.score, 4), 
                "content": res.payload.get("content"),
                "type": res.payload.get("type")
            } 
            for res in results
        ]
        
        import json
        return json.dumps(formatted_results, indent=2)
    
    except UnexpectedResponse as e:
        if "Not found: Collection" in str(e):
            return "ERROR: Collection not found. Did you run create_session_collection first?"
        return f"ERROR: Qdrant search failed. Details: {str(e)}"
    except Exception as e:
        return f"ERROR: Search operation failed. Details: {str(e)}"

if __name__ == "__main__":
    mcp.run()