# Exploration: deep-agents-core

**Context7 Sources Consulted:**
- `/langchain-ai/deepagents` — Official deepagents Python package (542 snippets, 82k tokens)
- `/websites/langchain_oss_python_deepagents` — Standalone doc site (1615 snippets, 177k tokens)
- `/langchain-ai/deepagents-quickstarts` — Quickstart examples (139 snippets)

---

## Summary for Building a Minimal Agent with Tool Calling Against Local Ollama

### 1. Minimal Setup — 3 lines of code
Install `deepagents` and `langchain-ollama`, then create an agent with a plain Python function as a tool (no `@tool` decorator required) and pass `model="ollama:devstral-2"`:

```bash
pip install -qU deepagents langchain-ollama
```

```python
from deepagents import create_deep_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model="ollama:devstral-2",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
```

**Prerequisites:** Ollama running locally with the model pulled (`ollama pull devstral-2`). No API key required for local use.

### 2. Harness Architecture — Under the Hood
`create_deep_agent()` returns a compiled **LangGraph `CompiledStateGraph`**. Internally it:
- Resolves the model via `init_chat_model("ollama:devstral-2")` or accepts a raw `BaseChatModel` (e.g. `ChatOllama(model="llama3")`)
- Builds a middleware stack: TodoList → Filesystem → Summarization → PromptCaching → PatchToolCalls
- Wraps custom tools into the general-purpose subagent spec
- Delegates to LangChain's `create_agent()` with `recursion_limit=1000`
- The returned graph is fully compatible with LangGraph streaming, checkpointers, LangSmith tracing, etc.

### 3. Key Configuration Options for Local Models
- **Model strings**: Use `"ollama:model-name"` format with `init_chat_model()`, or pass a `ChatOllama` instance directly
- **Custom tools**: Accepts `BaseTool`, plain callables (function → auto-converted to tool), or dict definitions
- **System prompt**: Concatenated with `BASE_AGENT_PROMPT` automatically
- **thread_id**: Required for multi-turn conversation persistence (use `config={"configurable": {"thread_id": "user-123"}}`)
- **Built-in tools** (always available): `write_todos` (planning), `ls`/`read_file`/`write_file`/`edit_file`/`glob`/`grep` (filesystem), `task` (subagent delegation)

---

## Key Source Files Discovered

| File | Purpose |
|------|---------|
| `deepagents/graph.py` | `create_deep_agent()` factory — full signature, middleware assembly, LangGraph compilation |
| `libs/cli/README.md` | CLI install with `DEEPAGENTS_EXTRAS="ollama"` |
| `libs/evals/MODEL_GROUPS.md` | Ollama provider group — 13 supported models |
| `libs/cli/deepagents_cli/model_config.py` | Model provider config mapping for CLI |
| `libs/deepagents/THREAT_MODEL.md` | System architecture overview — LangGraph `CompiledStateGraph` return type |

---

## Context7 Raw Documentation Snippets Referenced

1. **"Create and Run a Deep Agent"** (`docs.langchain.com/oss/python/deepagents`) — Minimal example with `model="ollama:devstral-2"` and plain function as tool
2. **"Create Deep Agent with Ollama"** (`docs.langchain.com/oss/python/deepagents/deep-research`) — Uses `init_chat_model(model="ollama:devstral-2")` with subagents
3. **"Create a Deep Agent"** (`docs.langchain.com/oss/python/deepagents/overview`) — Overview of Ollama integration via `langchain-ollama` and `ollama:model-name` identifiers
4. **"create_deep_agent — Main Agent Factory"** (`github.com/langchain-ai/deepagents/blob/main/deepagents/libs/deepagents/deepagents/graph.py`) — Full source of factory function showing middleware stack, `create_agent()` delegation, and `CompiledStateGraph` return
5. **"Install Deep Agents CLI with Model Provider Extras"** (`github.com/langchain-ai/deepagents/blob/main/libs/cli/README.md`) — `DEEPAGENTS_EXTRAS="nvidia,ollama"` install patterns
6. **"Integrating Custom Tools into Deep Agents"** (`docs.langchain.com/oss/python/deepagents/customization`) — Plain function passed directly to `tools=[]`
7. **"Set API Keys for Ollama and Tavily"** (`docs.langchain.com/oss/python/deepagents/quickstart`) — No env var needed for local Ollama; `OLLAMA_API_KEY` for hosted inference

---

## Dependencies for Ollama Workflow

```
deepagents >= 0.3.5
langchain
langgraph >= 1.0.6
langchain-ollama    # Ollama integration
langchain-community  # Alternative ChatOllama source
```
