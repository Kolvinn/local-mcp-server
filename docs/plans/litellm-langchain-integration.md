# Plan: LiteLLM + LangChain/LangGraph Integration

## Goal
Replace direct opencode upstream calls with LiteLLM as a unified routing/proxy layer. LangChain code talks to one endpoint; LiteLLM handles Ollama local + opencode upstream with automatic fallbacks on rate limits.

---

## Part 1 — LiteLLM Config (run yourself, container or pip)

**File:** `litellm_config.yaml`

```yaml
model_list:
  # Local Ollama models
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://host.docker.internal:11434"
      keep_alive: "8m"

  - model_name: "devstral"
    litellm_params:
      model: "ollama/devstral"
      api_base: "http://host.docker.internal:11434"
      keep_alive: "8m"

  # OpenCode upstream (with fallback to local)
  - model_name: "deepseek-flash"
    litellm_params:
      model: "openai/deepseek-v4-flash"
      api_base: "https://opencode.ai/zen/go/v1"
      api_key: "${OPENCODE_API_KEY}"          # set in env, not hardcoded
      reasoning_effort: "low"

router_settings:
  fallbacks:
    - {"deepseek-flash": ["llama3.1", "devstral"]}
  allowed_fails: 3
  cooldown_time: 30

litellm_settings:
  drop_params: true  # drop unsupported provider params
```

**Start LiteLLM:**
```bash
# Docker
docker run -v $(pwd)/litellm_config.yaml:/config.yaml \
  -e OPENCODE_API_KEY="$OPENCODE_API_KEY" \
  -p 4000:4000 \
  ghcr.io/berriai/litellm:main-stable \
  --config /config.yaml --port 4000

# OR pip
pip install litellm
litellm --config litellm_config.yaml
```

**Verify it's up:**
```bash
curl http://localhost:4000/health
```

---

## Part 2 — Update test_langchain.py

**Changes to make in `src/tests/test_langchain.py`:**

1. **Replace the ChatOpenAI setup** (lines 16-21):
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    base_url="http://localhost:4000/v1",   # LiteLLM proxy
    api_key="fake-key",                     # LiteLLM doesn't require real key for local
    model="llama3.1",                       # pick any model from litellm_config.yaml
)
```

2. **Keep everything else** — the `create_deep_agent`, tools, streaming loop all stay the same.

**Run it:**
```bash
cd src && .venv/bin/python -m pytest tests/test_langchain.py -v -s
```

---

## Part 3 — Test Failover (deliberately trigger it)

Once Part 2 works, test that fallback actually works:

1. Configure a second `litellm_config.yaml` with a fake bad endpoint that immediately rate-limits
2. Set fallbacks to point to `llama3.1`
3. Invoke with `model="bad-model"` and verify it falls back

Or simpler: just point at `deepseek-flash` (your upstream), let LiteLLM handle rate limits naturally if they occur.

---

## Part 4 — Wire Into Deep Agents CLI (optional, stretch goal)

Once the agent works via LangChain/LiteLLM, connect to the CLI:

```bash
# Option A: stdin pipe (simplest, non-interactive)
echo "say hi and invoke print_hello" | deepagents

# Option B: ACP server (programmatic, supports streaming)
# In Python:
from deepagents import AgentServerACP
from deepagents import create_deep_agent

agent = create_deep_agent(model="openai/gpt-4", tools=[...])
server = AgentServerACP(agent)
server.run()  # exposes on stdio
```

---

## File Locations

| File | Purpose |
|------|---------|
| `litellm_config.yaml` | LiteLLM routing + fallback config |
| `src/tests/test_langchain.py` | Test file to modify |
| `.env` | Contains `OPENCODE_API_KEY` |

---

## Key Benefits When Done

- LangChain code never references opencode directly
- One `ChatOpenAI(base_url="http://localhost:4000/v1")` for everything
- Rate limits on `deepseek-flash` auto-failover to local Ollama
- Swap models by editing `litellm_config.yaml` — no code changes