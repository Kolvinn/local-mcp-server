# Memory Manager MVP — Agent Endpoint

> **Sibling docs:** [mvp-overview.md](mvp-overview.md) | [mvp-checklist.md](mvp-checklist.md) | [mvp-relationships.md](mvp-relationships.md)
> **Reference:** `src/tests/test_langchain.py` — working LiteLLM + Deep Agent setup

## Goal

Wrap the memory manager as LangChain tools so any agent (orchestrator, user-facing agent, subagent) can call `ingest_memory`, `search_memory`, and `retrieve_context`. The agent itself uses **LiteLLM** as the model pivot — same pattern as `test_langchain.py`.

## What This Looks Like

```python
# The agent is created ONCE, then called with config
agent = create_memory_agent()   # wraps memory manager tools

config = {"configurable": {"thread_id": "session-abc"}}

# User or orchestrator calls:
agent.invoke({
    "messages": [{"role": "user", "content": "Search memory for qdrant issues"}]
}, config=config)

# Agent autonomously calls search_memory tool, returns results
```

## Stack Position

```
User / Orchestrator / Other Agents
        │
        ▼
┌──────────────────────────────────┐
│  Memory Agent (LangChain)         │
│  Model: ChatLiteLLM               │
│  → openai/deepseek-flash          │
│                                   │
│  Tools:                           │
│    ingest_memory(path)            │
│    search_memory(query)           │
│    retrieve_context(query)        │
│    get_memory_status()            │
│                                   │
│  Infrastructure:                  │
│    MemorySaver (checkpointer)     │
│    thread_id for persistence      │
├──────────────────────────────────┤
│  Memory Manager (src/memory/)     │
│  ingest / search / retrieve       │
├──────────────┬───────────────────┤
│  Qdrant      │  DictGraphStore   │
└──────────────┴───────────────────┘
```

## Tool Definitions

### Tool 1: `ingest_memory`

```python
@tool
def ingest_memory(path: str) -> str:
    """Ingest a file into memory. Accepts a file path.
    Classifies, chunks, embeds, stores in Qdrant and graph.
    Returns summary of what was stored."""
```

**What it calls:** `src/memory/ingest.ingest_file(path)` — the full Phase 3 pipeline.

**Agent uses this when:** User says "remember this file" or orchestrator ingests session output.

**Returns:** `"Ingested 5 chunks: 2 bugs, 1 decision, 2 technical_facts. Created 3 graph nodes, 4 edges."`

---

### Tool 2: `search_memory`

```python
@tool
def search_memory(query: str, limit: int = 5) -> str:
    """Semantic search across stored memory. Returns relevant chunks
    with their categories and tags. Use for finding specific facts."""
```

**What it calls:** `src/memory/retrieve.search(query, limit)` — Phase 4.1.

**Agent uses this when:** User asks a question the agent doesn't know. Orchestrator's ORIENT phase.

**Returns:** Formatted list of chunks with content, category, tags, source.

---

### Tool 3: `retrieve_context`

```python
@tool
def retrieve_context(query: str, limit: int = 5) -> str:
    """Deep context retrieval. Searches memory AND expands via
    graph relationships. Returns enriched context including related
    items the user didn't explicitly ask for. Use for thorough research."""
```

**What it calls:** `src/memory/retrieve.retrieve_context(query, limit)` — Phase 4.2.

**Agent uses this when:** Orchestrator's GATHER phase. User asks "tell me everything about X."

**Returns:** Vector hits + 1-hop graph neighbors, deduplicated, with relationship context.

---

### Tool 4: `get_memory_status`

```python
@tool
def get_memory_status() -> str:
    """Check memory manager status: total chunks, graph nodes, categories."""
```

**What it calls:** Qdrant `count()` + graph node count.

**Agent uses this when:** User asks "what's in memory?" or agent needs to know if ingestion is needed.

**Returns:** `"Memory: 142 chunks, 38 graph nodes (12 Bug, 8 Decision, 18 Component). Last ingest: unknown."`

---

## Agent Creation

Based on the working pattern in `src/tests/test_langchain.py`:

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_litellm import ChatLiteLLM
import os

LITE_LLM_URL = os.getenv("LITE_LLM_URL", "http://litellm:4000")
LITE_LLM_API_KEY = os.getenv("LITE_LLM_API_KEY", "sk-1234")

def create_memory_agent():
    model = ChatLiteLLM(
        api_base=LITE_LLM_URL,
        api_key=LITE_LLM_API_KEY,
        model="openai/deepseek-flash",
    )

    checkpointer = MemorySaver()

    agent = create_deep_agent(
        model=model,
        tools=[ingest_memory, search_memory, retrieve_context, get_memory_status],
        system_prompt=(
            "You are a memory manager. You help users store and retrieve "
            "knowledge. Use ingest_memory to store files. Use search_memory "
            "for quick lookups. Use retrieve_context for deep research that "
            "includes related context. Always cite sources when returning results."
        ),
        checkpointer=checkpointer,
    )

    return agent
```

**Key decisions:**
- `create_deep_agent` (not `create_agent`) — gives built-in filesystem tools + planning + subagents for free
- `MemorySaver` — enables multi-turn conversations with same `thread_id`
- No `interrupt_on` needed — memory tools are read-only (except ingest, which is intentional)
- No `Store` needed — single-session persistence is sufficient for MVP
- No `SkillsMiddleware` — tools are defined inline, not loaded from SKILL.md files

---

## Acceptance Criteria

### AC-1: Agent invokes search_memory autonomously
- **Given:** Agent created with memory tools
- **When:** User says "what embedding model do we use?"
- **Then:** Agent calls `search_memory("embedding model")` and returns result

### AC-2: Agent invokes retrieve_context for deep queries
- **Given:** Memory has ingested `docs/context/stack.md`
- **When:** User says "tell me everything about Qdrant setup"
- **Then:** Agent calls `retrieve_context("Qdrant setup")` and returns expanded results

### AC-3: Agent handles missing tools gracefully
- **Given:** Agent is asked something outside its memory tools
- **When:** User says "write a poem"
- **Then:** Agent responds without calling memory tools (uses its LLM knowledge)

### AC-4: Multi-turn memory persists within session
- **Given:** Same `thread_id` across two invocations
- **When:** Turn 1: "ingest docs/context/stack.md". Turn 2: "what did I just ingest?"
- **Then:** Agent remembers the ingestion from turn 1 and answers correctly.

---

## File

| File | Purpose |
|------|---------|
| `src/agents/__init__.py` | Package init |
| `src/agents/memory_agent.py` | Tool definitions + `create_memory_agent()` |
| `src/tests/test_memory_agent.py` | Agent integration tests |

## Dependencies

- `langchain_litellm` — already installed (used in test_langchain.py)
- `deepagents` — already installed (used in test_langchain.py)
- `langgraph.checkpoint.memory.MemorySaver` — already installed
- `src/memory/` — Phase 0-4 must be complete before Phase 5 works
