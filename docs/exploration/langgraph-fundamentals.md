# Exploration: LangGraph Fundamentals

**Date:** 2026-05-08
**Source:** Context7 API (LangGraph Python docs at `langchain_oss_python_langgraph`), SKILL.md at `.opencode/skills/langgraph-fundamentals/SKILL.md`

---

## Summary

- **Minimal streaming agent with tool calling** requires: (1) define state with `MessagesState` (built-in messages reducer), (2) add `llm_call` node + `tool_node` (from `langgraph.prebuilt.ToolNode` or manual), (3) wire with `START → llm_call`, conditional edge to `tool_node` or `END`, and back-edge `tool_node → llm_call`, (4) compile and `.stream()` with `stream_mode=["values", "messages"]` for both state snapshots and token-by-token LLM output.
- **Checkpointing + interrupts** are essential for production agents: compile with `MemorySaver()` checkpointer to enable persistence, thread-based conversations (`thread_id` in config), and breakpoints via `interrupt_before=`/`interrupt_after=` or the `interrupt()` function inside nodes. Resume with `Command(resume=...)`.
- **The v2 streaming format** unifies all stream modes (`values`, `updates`, `messages`, `custom`) under a single `{"type": ..., "data": ...}` envelope, enabling type-narrowed handling. Use `version="v2"` for consistent consumption.

---

## 1. StateGraph Basics — State, Nodes, Edges

**Source:** Context7 (docs.langchain.com/oss/python/langgraph/pregel, /graph-api, /streaming)

### State Definition
```python
from typing import TypedDict
from langgraph.graph import StateGraph, MessagesState, START, END

# Option A: Simple TypedDict
class State(TypedDict):
    topic: str
    joke: str

# Option B: With built-in message reducer
class AgentState(MessagesState):
    classification: str
    research: str
```

### Graph Construction Pattern
```python
builder = StateGraph(State)
builder.add_node("node_name", node_function)     # Add node
builder.add_edge(START, "node_name")              # Entry edge
builder.add_edge("node_a", "node_b")              # Static edge
builder.add_conditional_edges("node_a", router, ["target_b", END])  # Dynamic
graph = builder.compile()                          # Must compile before use
```

### Key Rules
- Nodes return **partial state dicts** (not full state, not mutations)
- Lists need reducers (`Annotated[list, operator.add]`) or use `MessagesState` (built-in)
- `START` is entry-only — cannot route back to it
- `compile()` is required before `invoke()` or `stream()`

---

## 2. Creating a Simple ReAct Agent

**Source:** Context7 (docs.langchain.com/oss/python/langgraph/quickstart, /workflows-agents)

There are two approaches:

### Approach A: StateGraph API (manual but explicit)
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain.messages import SystemMessage, ToolMessage

def llm_call(state: MessagesState):
    return {"messages": [llm_with_tools.invoke([SystemMessage(...)] + state["messages"])]}

def tool_node(state: dict):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

def should_continue(state) -> Literal["tool_node", END]:
    return "tool_node" if state["messages"][-1].tool_calls else END

agent = (
    StateGraph(MessagesState)
    .add_node("llm_call", llm_call)
    .add_node("tool_node", tool_node)
    .add_edge(START, "llm_call")
    .add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    .add_edge("tool_node", "llm_call")  # loop back
    .compile()
)
```

### Approach B: Functional API (`@task`/`@entrypoint`)
- Use `@task` decorators for `call_llm` and `call_tool` functions
- Use `@entrypoint()` for the agent function with a `while True` loop
- Stream with `agent.stream(messages, stream_mode="updates")`

### Note on `create_react_agent`
The Context7 docs primarily demonstrate the manual StateGraph approach rather than the prebuilt `create_react_agent` from `langgraph.prebuilt`. The manual approach provides finer-grained control. For a quick prebuilt agent, import `from langgraph.prebuilt import create_react_agent` and call `create_react_agent(model, tools)`.

---

## 3. Streaming — stream_mode Options

**Source:** Context7 (docs.langchain.com/oss/python/langgraph/streaming)

### Stream Modes (v2 format)

| Mode | What it Streams | Use Case |
|------|----------------|----------|
| `"values"` | Full state after each superstep | Monitor complete state progression |
| `"updates"` | State deltas (only changed keys per node) | Track which node changed what |
| `"messages"` | LLM tokens + metadata tuple | Real-time chat UI (token-by-token) |
| `"custom"` | User-defined data from `get_stream_writer()` | Progress indicators, status updates |
| `"checkpoints"` | Checkpoint events | Requires checkpointer; replay/debug |

### v2 Unified Format (recommended)
```python
# All modes produce same envelope: {"type": str, "data": any}
for part in graph.stream(inputs, stream_mode=["values", "messages"], version="v2"):
    if part["type"] == "values":
        print(f"Full state: {part['data']}")
    elif part["type"] == "messages":
        msg_chunk, metadata = part["data"]
        print(msg_chunk.content, end="", flush=True)
```

### Custom Data from Nodes/Tools
```python
from langgraph.config import get_stream_writer

def my_node(state):
    writer = get_stream_writer()
    writer({"progress": 50, "status": "working..."})
    return {"result": "done"}

# Must use stream_mode="custom" to receive
for chunk in graph.stream(inputs, stream_mode="custom", version="v2"):
    if chunk["type"] == "custom":
        print(chunk["data"])
```

---

## 4. Checkpointing with MemorySaver

**Source:** Context7 (docs.langchain.com/oss/python/langgraph/persistence, /add-memory, /streaming)

### Setup
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Each conversation needs a unique thread_id
config = {"configurable": {"thread_id": "user-session-1"}}
result = graph.invoke({"messages": [input_msg]}, config)
```

### What Checkpointing Enables
- **Thread persistence** — state survives across multiple invocations with the same `thread_id`
- **Time travel** — `get_state_history(config)` to list past states, replay from any checkpoint
- **Interrupts** — required for `interrupt_before`/`interrupt_after` and `interrupt()` to work
- **Subgraph scoping** — `compile(checkpointer=False)` for stateless subgraphs, `True` for per-thread

### Production Alternatives
- `PostgresSaver` from `langgraph.checkpoint.postgres`
- `RedisSaver` from `langgraph.checkpoint.redis`

---

## 5. Interrupts and Human-in-the-Loop

**Source:** Context7 (docs.langchain.com/oss/python/langgraph/interrupts, /use-time-travel, /graph-api)

### Two Ways to Set Interrupts

**A. Static (compile-time or invoke-time):**
```python
# At compile time
graph = builder.compile(checkpointer=cp, interrupt_before=["node_a"])

# At invoke time (overrides compile-time)
graph.invoke(inputs, interrupt_after=["node_b", "node_c"], config=config)
```

**B. Dynamic (inside a node):**
```python
from langgraph.types import interrupt, Command

def ask_user(state):
    user_input = interrupt("What is your name?")  # pauses, waits for resume
    return {"value": [f"Hello, {user_input}!"]}
```

### Resume Pattern
```python
# First invoke hits the interrupt
graph.invoke(inputs, config)

# Resume by passing Command with resume value
graph.invoke(Command(resume="Alice"), config)

# The interrupt() call in the node returns "Alice"
```

### Forking Between Interrupts
- Use `graph.get_state_history(config)` to find a checkpoint
- Use `graph.update_state(checkpoint.config, {...})` to fork before an interrupt
- Resume the forked execution with `graph.invoke(Command(resume=...), fork_config)`

### Requirements
- A **checkpointer is required** for interrupts (MemorySaver or similar)
- A **thread_id** in config is required

---

## Key Insights for a Minimal Streaming Agent with Tool Calling

1. **State:** Use `MessagesState` — it already includes `messages: Annotated[list, add_messages]` (the correct reducer for message accumulation).

2. **Nodes:** Two essential nodes — `llm_call` (invokes model with tools bound) and `tool_node` (executes tool calls). The `ToolNode` from `langgraph.prebuilt` handles tool execution and error recovery automatically.

3. **Graph Topology:** `START → llm_call → (conditional: tool_node or END) → tool_node → llm_call (loop back)`. This creates the ReAct loop.

4. **Streaming for UI:** Use `stream_mode=["values", "messages"]` with `version="v2"`. The `"messages"` mode gives token-by-token LLM output for real-time display. The `"values"` mode gives full state snapshots after each step (including tool results).

5. **Persistence:** Compile with `MemorySaver()` checkpointer and pass `thread_id` in config. This enables conversation continuity and interrupt support.

6. **Human-in-the-Loop:** For approval flows, use `interrupt()` inside a `human_review` node. Resume with `Command(resume=...)`. The `langgraph-human-in-the-loop` skill covers this in detail.
