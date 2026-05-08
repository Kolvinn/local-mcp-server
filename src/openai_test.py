import openai
import os

OPENCODE_GO_KEY = os.getenv(
    "OPENCODE_GO_API_KEY",
    "",
)
OPENCODE_GO_URL = "https://opencode.ai"
MODEL_NAME = "deepseek-v4-flash"

# Assuming default local ports for Qdrant and Ollama
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION_NAME = "test_agent_memories"

# # Configure the client for OpenCode Go
# client = openai.OpenAI(
#     api_key="OPENCODE_GO_KEY",                # From opencode.ai/auth
#     base_url="https://api.opencode.go/v1"                 # Standard OpenCode compatible endpoint
# )

# # Make a request
# response = client.chat.completions.create(
#     model=MODEL_NAME,                   # Use a model listed via /models
#     messages=[{"role": "user", "content": "say hello."}]
# )

# print(response.choices[0].message.content)


client = openai.OpenAI(
    api_key=OPENCODE_GO_KEY,
    # FIX: Add /v1 to the endpoint
    base_url="https://opencode.ai/zen/go/v1",
)

try:
    response = client.chat.completions.create(
        # FIX: Ensure this matches a valid ID from the /models endpoint
        model=MODEL_NAME,
        messages=[{"role": "user", "content": "Hello, are you connected?"}],
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Connection Error: {e}")
