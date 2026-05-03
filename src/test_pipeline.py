import os
import uuid
import json
from typing import List, Literal

import instructor
import openai
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
import ollama

# =====================================================================
# 1. CONFIGURATION & SECRETS
# =====================================================================
# Replace with your actual OpenCode Go key
OPENCODE_GO_KEY = os.getenv(
    "OPENCODE_GO_API_KEY",""
)
OPENCODE_GO_URL = "https://opencode.ai/zen/go/v1"
MODEL_NAME = "deepseek-v4-flash"

# Assuming default local ports for Qdrant and Ollama
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION_NAME = "test_agent_memories"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIMS = os.getenv("EMBEDDING_DIMS", "768")
# =====================================================================
# 2. SCHEMA DEFINITION (The "Contract")
# =====================================================================
class MemoryMetadata(BaseModel):
    category: Literal["procedural", "declarative", "objective"] = Field(
        ...,
        description="Must be 'procedural' for AI rules/behavioral overrides, 'declarative' for general facts, or 'objective' for goals.",
    )
    sub_type: str = Field(
        ...,
        description="A short 1-2 word classification (e.g., 'coding_style', 'project_fact')",
    )
    tags: List[str] = Field(
        default_factory=list, description="3 to 5 keyword tags for the content."
    )


# =====================================================================
# 3. SERVICE INITIALIZATION
# =====================================================================
print("Initializing services...")


llm_client = instructor.from_openai(
    openai.OpenAI(api_key=OPENCODE_GO_KEY, base_url="https://opencode.ai/zen/go/v1"),
    mode=instructor.Mode.JSON,
)

# B. Qdrant Client
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
o_client = ollama.Client(host=OLLAMA_URL)
# print(o_client.list())
# # Reset collection for testing purposes
# if qdrant.collection_exists(COLLECTION_NAME):
#     qdrant.delete_collection(COLLECTION_NAME)

# qdrant.create_collection(
#     collection_name=COLLECTION_NAME,
#     vectors_config=rest.VectorParams(
#         size=EMBEDDING_DIMS,  # Default for nomic-embed-text
#         distance=rest.Distance.COSINE,
#     ),
# )
print(f"[*] Qdrant collection '{COLLECTION_NAME}' ready.")

# =====================================================================
# 4. CORE PIPELINE FUNCTIONS
# =====================================================================

def ollama_embed(raw_text):
    embed_response = o_client.embed(
                model=EMBEDDING_MODEL, input=raw_text, dimensions=EMBEDDING_DIMS
            )
    return embed_response["embeddings"][0]

def process_and_store(raw_text: str):
    print(f"\n--- PROCESSING: '{raw_text[:50]}...' ---")
    try:
        # STEP 1: Metadata Extraction via OpenCode Go (Instructor)
        print("-> [DEBUG] Contacting OpenCode Go for Metadata...")
        try:
            metadata: MemoryMetadata = llm_client.chat.completions.create(
                model=MODEL_NAME,
                response_model=MemoryMetadata,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data classification engine. Categorize the user's input accurately.",
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this input for memory storage: {raw_text}",
                    },
                ],
            )
            print(
                f"   [SUCCESS] Category: {metadata.category.upper()} | Sub-type: {metadata.sub_type}"
            )
        except Exception as e:
            print(f"   [ERROR] Metadata Extraction Failed: {str(e)}")
            return  # Exit early as we cannot proceed without metadata

        # STEP 2: Vector Embedding via Local Ollama
        print("-> [DEBUG] Generating Vector via Ollama...")
        try:

            vector = ollama_embed(raw_text)
            print(f"   [SUCCESS] Vector length: {len(vector)}")
        except Exception as e:
            print(f"   [ERROR] Ollama Embedding Failed: {str(e)}")
            print("   Check if Ollama is running (`ollama serve`) and model is pulled.")
            return

        # STEP 3: Storage in Qdrant
        print("-> [DEBUG] Upserting to Qdrant...")
        try:
            doc_id = str(uuid.uuid4())

            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    rest.PointStruct(
                        id=doc_id,  # Unique integer or UUID
                        vector=vector,
                        payload= {
                            "sys_type": metadata.category,
                            "sys_subtype": metadata.sub_type,
                            "user_tags": metadata.tags,
                            "content": raw_text,
                        }
                    )
                ]
            )
            print(f"   [SUCCESS] Stored in Qdrant with ID: {doc_id}")
        except Exception as e:
            print(f"   [ERROR] Qdrant Storage Failed: {str(e)}")
            print("   Verify Qdrant is listening on port 6333.")
            return

    except KeyboardInterrupt:
        print("\n[!] User interrupted process.")
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Unexpected error in pipeline: {str(e)}")



def search_memory(query: str, enforce_category: str = None):
    print(f"\n--- SEARCHING: '{query}' ---")
    if enforce_category:
        print(f"-> Applying Strict Metadata Filter: sys_type == '{enforce_category}'")
    else:
        print("-> No metadata filter applied (Global Search)")

    # 1. Embed the query
    query_vector = ollama_embed(query)

    # 2. Build Filter (if requested)
    query_filter = None
    if enforce_category:
        query_filter = rest.Filter(
            must=[
                rest.FieldCondition(
                    key="sys_type", match=rest.MatchValue(value=enforce_category)
                )
            ]
        )

    # 3. Execute Search
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=3,
    )

    print("-> Results:")
    if not results:
        print("   No matches found.")
    for r in results.points:
        print(
            f"   Score: {r.score:.3f} | Type: {r.payload['sys_type']} | Content: {r.payload['content']}"
        )


# =====================================================================
# 5. EXECUTION & TEST SCENARIOS
# =====================================================================
if __name__ == "__main__":
    # Test Data: A mix of general facts and behavioral rules
    # test_inputs = [
    #     "The project backend is built using Python and FastAPI.",
    #     "Whenever you write Python code, you must strictly use Type Hints and follow PEP8.",
    #     "The server deployment budget for Q3 is $5,000.",
    #     "Never use recursive functions when traversing the file system; always use iterative loops.",
    # ]

    # # Run the storage pipeline
    # for text in test_inputs:
    #     process_and_store(text)

    # print("\n" + "=" * 50)
    # print("TESTING RETRIEVAL LOGIC (Separation of Concerns)")
    # print("=" * 50)

    # Scenario A: The AI is about to write code and needs its "Rules" (Procedural)
    # We force the 'procedural' filter so it doesn't accidentally fetch the "Python backend" fact.
    search_memory("How should I write Python code?", enforce_category="procedural")

    # Scenario B: The AI needs general context (Declarative)
    search_memory("What language is the backend in?", enforce_category="declarative")

    # Scenario C: Global search (To see what happens without filters)
    search_memory("Python")
