# Exploration: LangChain Dependencies & Ollama Integration

**Date:** 2026-05-08
**Skill Source:** `/home/dev/app/.opencode/skills/langchain-dependencies/SKILL.md`
**Context7 Queries:** LangChain, LangGraph, Ollama Python libraries

---

## Summary (2-3 bullets)

- There are **two ways** to connect LangChain to a local Ollama instance: the preferred `langchain-ollama` package (with `ChatOllama`, full tool-calling/structured-output support, defaults to `http://localhost:11434`) or the lightweight `langchain-openai` package using `ChatOpenAI` pointed at Ollama's OpenAI-compatible endpoint (`http://localhost:11434/v1`). The latter misses non-standard response fields but works for basic chat.
- **Minimum ecosystem requirements:** Python 3.10+, `langchain>=1.0,<2.0`, `langchain-core>=1.0,<2.0`, `langsmith>=0.3.0`. For LangGraph add `langgraph>=1.0,<2.0`. For Deep Agents add `deepagents` (requires Python 3.11+). LangChain 0.3 is legacy/maintenance-only.
- **Key compatibility constraint:** `langchain-community` does NOT follow semver — pin to a minor series (e.g. `>=0.4.0,<0.5.0`). Always prefer dedicated integration packages (like `langchain-ollama`, `langchain-openai`) over `langchain-community` for stability.

---

## Key Findings

### 1. Required Python Packages

| Package | Purpose | Min Version |
|---------|---------|-------------|
| `langchain` | Core framework | >=1.0,<2.0 |
| `langchain-core` | Base types & interfaces | >=1.0,<2.0 |
| `langsmith` | Tracing & evaluation | >=0.3.0 |
| `langgraph` | Graph orchestration (optional) | >=1.0,<2.0 |
| `deepagents` | Deep Agents framework (optional) | latest (requires Python 3.11+) |
| `langchain-ollama` | Ollama integration (preferred) | latest |
| `langchain-openai` | OpenAI / OpenAI-compatible APIs | latest |

**Environment:** Python 3.10+ required (LangGraph CLI needs 3.11+). Node.js 20+ for TypeScript.

### 2. Configuring ChatOpenAI to Use Ollama (OpenAI Compatibility API)

**Pattern — generic OpenAI-compatible endpoint:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",  # Ollama's OpenAI-compatible endpoint
    api_key="ollama",                       # Ollama doesn't require a real key
    model="llama3.1",                       # Any model you've pulled in Ollama
    temperature=0,
)
```

**How it works:** Ollama exposes an OpenAI-compatible Chat Completions API at `http://localhost:11434/v1`. LangChain's `ChatOpenAI` class can target any OpenAI-compatible endpoint by setting `base_url`.

**Important caveat from LangChain docs:** `ChatOpenAI` targets official OpenAI API specifications only. It does not extract or preserve non-standard response fields from third-party providers (e.g., `reasoning_content`, `reasoning_details`). Use the provider-specific package (`langchain-ollama`) when access to non-standard features is required.

### 3. Two Approaches to Connect LangChain ↔ Ollama

| Aspect | `langchain-ollama` (Preferred) | `langchain-openai` (Compatibility) |
|--------|-------------------------------|-----------------------------------|
| Install | `pip install langchain-ollama` | `pip install langchain-openai` |
| Class | `ChatOllama` | `ChatOpenAI` |
| Default URL | `http://localhost:11434` (customizable via `base_url`) | Must set `base_url="http://localhost:11434/v1"` |
| Tool calling | ✅ Full support via `.bind_tools()` | ✅ Works (standard OpenAI format) |
| Structured output | ✅ `withStructuredOutput` | ✅ Works |
| Image input | ✅ Supported | ❌ Not guaranteed |
| Streaming | ✅ Token-level | ✅ Token-level |
| Non-standard fields | ✅ Preserved | ❌ Not extracted |
| Async | ✅ Native async | ✅ |
| Logprobs | ✅ Supported | ✅ |

**Example — ChatOllama (preferred):**
```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="llama3.1",
    temperature=0,
)
```

### 4. Known Compatibility Issues

| Issue | Detail |
|-------|--------|
| **langchain-community NOT semver** | Minor releases can contain breaking changes. Pin to exact minor: `>=0.4.0,<0.5.0`. |
| **ChatOpenAI misses non-standard fields** | If your Ollama model returns custom fields (reasoning, etc.), ChatOpenAI won't expose them — use `ChatOllama` instead. |
| **LangChain 0.3 is legacy** | Maintenance-only until Dec 2026. Start new projects on 1.0 LTS. |
| **langchain-core is a peer dependency** | Must be explicitly installed alongside `langchain` in monorepos/yarn workspaces. |
| **Deep Agents requires Python 3.11+** | Standard LangChain/LangGraph only needs 3.10+, but Deep Agents needs 3.11+. |
| **Dedicated packages preferred** | Always use `langchain-chroma` over community Chroma, `langchain-ollama` over community Ollama, etc. |
| **LangGraph v1 backwards compatible** | Main change: `create_react_agent` deprecated in favor of `create_agent`. |
| **langchain-ollama custom base_url** | Python supports custom `base_url` via kwargs; TS `@langchain/ollama` added custom `baseUrl` in v1.1.0. |

### 5. Minimal Requirements for LangChain + Ollama Project

```txt
# requirements.txt
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langsmith>=0.3.0
langchain-ollama           # <-- preferred Ollama integration

# OR (if using OpenAI compatibility approach):
# langchain-openai
```

If using LangGraph:
```txt
langgraph>=1.0,<2.0
```

If using Deep Agents:
```txt
deepagents                  # bundles langgraph internally
# Requires Python 3.11+
```

### 6. Context7 Sources Referenced

- LangChain Python docs — Installation, Providers & Models, ChatOllama integration, vLLM ChatOpenAI example
- LangGraph docs — Installation (Python 3.10+), v1 migration guide
- Ollama Python Library docs — Custom client configuration, cloud API
- Deep Agents docs — Installation (Python 3.11+)
