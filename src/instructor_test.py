import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Literal


# 1. Define the Schema (The "Contract")
class MemoryMetadata(BaseModel):
    category: Literal["procedural", "declarative", "objective"] = Field(
        ..., description="Procedural for rules/overrides, Declarative for facts."
    )
    sub_type: str = Field(..., description="e.g., 'coding_style', 'project_milestone'")
    tags: List[str] = Field(default_factory=list)
    summary: str = Field(..., description="A 1-sentence distillation for the graph.")


# 2. Patch the Client for OpenCode Go
client = instructor.from_openai(
    OpenAI(
        base_url="https://api.opencode.go/v1",
        api_key="sk-ce5XahbeNcIM30Tjz3eb5N4hnI5zWSHnXtfGk1VlPnUe6bt0vs0fbfM8zZXfm7KP",
    ),
    mode=instructor.Mode.JSON,
)


async def process_and_store(raw_text: str):
    # 3. Extract Structured Metadata
    metadata = client.chat.completions.create(
        model="deepseek-flash",
        response_model=MemoryMetadata,
        messages=[
            {
                "role": "user",
                "content": f"Analyze this input for memory storage: {raw_text}",
            }
        ],
    )
    print(metadata)
    # 4. Use Metadata to Drive the Separation of Concerns
    # Push to Graphiti for temporal relations
    # await graphiti.add_episode(
    #     content=raw_text,
    #     metadata=metadata.model_dump()
    # )

    # # Push to Qdrant with the metadata as a strict filterable payload
    # qdrant.upsert(
    #     collection_name="agent_memories",
    #     points=[{
    #         "id": str(uuid.uuid4()),
    #         "vector": generate_embedding(raw_text),
    #         "payload": {
    #             "sys_type": metadata.category,
    #             "sys_subtype": metadata.sub_type,
    #             "user_tags": metadata.tags,
    #             "content": raw_text
    #         }
    #     }]
    # )

    return f"Stored as {metadata.category} | Tags: {metadata.tags}"
