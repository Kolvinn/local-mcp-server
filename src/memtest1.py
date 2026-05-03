from mem0 import Memory

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test",
            "host": "qdrant",
            "port": 6333,
            "embedding_model_dims": 768,  # Change this according to your local model's dimensions
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "opencode-go/deepseek-v4-flash",  # Example model
            "api_key": "sk-ce5XahbeNcIM30Tjz3eb5N4hnI5zWSHnXtfGk1VlPnUe6bt0vs0fbfM8zZXfm7KP",
            "openai_base_url": "https://opencode.ai/zen/go/v1/chat/completions",  # Example endpoint
            "temperature": 0.2,
        },
        # "provider": "ollama",
        # "config": {
        #     "model": "llama3.1:8b",
        #     "temperature": 0,
        #     "max_tokens": 2000,
        #     "ollama_base_url": "http://ollama:11434",  # Ensure this URL is correct
        # },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            # Alternatively, you can use "snowflake-arctic-embed:latest"
            "ollama_base_url": "http://ollama:11434",
        },
    },
}

# Initialize Memory with the configuration


def load():
    m = Memory.from_config(config)

    # Add a memory
    m.add("I'm visiting Paris", user_id="john")
    m.add("I'm taking a poopy", user_id="john")
    # Retrieve memories
    memories = m.get_all(filters={"user_id": "john"})
    ret = m.search("poop", top_k=1, filters={"user_id": "john"})
    print(memories)
    print(ret)
    print()


load()
