# LiteLLM + Ollama Integration — Exploration Findings

**Agent:** Explorer (read-only)  
**Skill:** context7  
**Source:** docs.litellm.ai (via Context7 API)  
**Date:** 2026-05-08

---

## 1. Model Name Format: `ollama/` vs `ollama_chat/` prefix

### Standard (`ollama/` prefix)
All Ollama models use the **`ollama/` prefix** in LiteLLM. The format is:
```
ollama/<model-name>
ollama/<model-name>:<tag>
```

**Examples from docs:**
- `ollama/mistral`
- `ollama/llama2`
- `ollama/llama2:13b`
- `ollama/llama2:70b`
- `ollama/llama3`
- `ollama/llama3:70b`
- `ollama/codellama`
- `ollama/orca-mini`
- `ollama/vicuna`
- `ollama/nous-hermes`
- `ollama/nous-hermes:13b`
- `ollama/wizard-vicuna`
- `ollama/mistral-7B-Instruct-v0.1`
- `ollama/mistral-7B-Instruct-v0.2`
- `ollama/mistral-8x7B-Instruct-v0.1`
- `ollama/mistral-8x22B-Instruct-v0.1`

> **DO NOT use bare model names (e.g., just `llama3`)** — always prefix with `ollama/`.

### Chat endpoint (`ollama_chat/` prefix)
For routing requests to Ollama's **`POST /api/chat`** endpoint (instead of `/api/generate`), use the `ollama_chat/` prefix:
- `ollama_chat/llama2`
- `ollama_chat/llama3.1`
- `ollama_chat/deepseek-r1`

**When to use which:**
| Prefix | Ollama Endpoint | Use Case |
|---|---|---|
| `ollama/` | `/api/generate` | Basic completion, FIM (Fill-in-Middle) via `prompt` param |
| `ollama_chat/` | `/api/chat` | Chat-formatted messages, tool/function calling |

> Tool calling **requires** `ollama_chat/` prefix.

---

## 2. `api_base` Format — Host vs Docker

### Local host (default)
```python
api_base="http://localhost:11434"
```
This is the default. Ollama runs on `localhost:11434` when installed natively.

### Explicit override
```python
api_base="http://localhost:11434"
```
If Ollama is not on the default port, specify explicitly.

### Docker considerations

**When running LiteLLM in Docker and Ollama on host:**
- On **Linux**: Use `http://host.docker.internal:11434` or the host's actual IP
- On **macOS/Windows**: Use `http://host.docker.internal:11434`
- Alternative: Use `--network host` on the LiteLLM container to access `localhost:11434`

**When running Ollama in Docker:**
```bash
docker run --name ollama litellm/ollama
```
Then LiteLLM connects to Ollama's container address (e.g., `http://ollama:11434` on a shared Docker network).

**Proxy config example:**
```yaml
model_list:
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"  # CHANGE THIS for Docker
```

**Starting proxy with Ollama model:**
```bash
litellm --model ollama/codellama
# INFO: Ollama running on http://0.0.0.0:8000
```

**Testing with OpenAI client:**
```python
import openai
api_base = "http://0.0.0.0:4000"  # LiteLLM proxy address
openai.api_base = api_base
openai.api_key = "temp-key"
```

---

## 3. `keep_alive` Parameter

The `keep_alive` parameter controls how long an Ollama model stays loaded in memory after the last request. This is an **Ollama-level** parameter passed through by LiteLLM.

### Usage in proxy config.yaml
```yaml
model_list:
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama_chat/llama3.1"
      keep_alive: "8m"       # Keep model loaded for 8 minutes
      # keep_alive: "-1"     # Keep model loaded FOREVER (never unload)
      # keep_alive: "0"      # Unload immediately after response
    model_info:
      supports_function_calling: true
```

### Values
| Value | Meaning |
|---|---|
| `"5m"` | Keep alive for 5 minutes (default in Ollama is 5m) |
| `"8m"` | Custom duration |
| `"30m"` | Half hour |
| `"1h"` | One hour |
| `"-1"` | **Forever** — model stays loaded in memory indefinitely |
| `"0"` | Unload immediately |

### Proxy-level keepalive (different concept)
There is also a **proxy keepalive timeout** for the LiteLLM proxy server itself (uvicorn connection keepalive):
```bash
litellm --keepalive_timeout 30
# or via env var:
export KEEPALIVE_TIMEOUT=75
```
This controls HTTP connection keepalive (not model persistence).

---

## 4. Function Calling / Tool Calling Support

### Overview
LiteLLM supports tool calling with Ollama models via the `ollama_chat/` prefix and the `tools` argument.

### Important: Native vs JSON-mode tool calling
- **Not all Ollama models support native function calling.** 
- LiteLLM **defaults to JSON mode** tool calls if native tool calling is not supported by the model.
- You can **optionally register** a model as supporting function calling:

```python
import litellm

litellm.register_model(model_cost={
    "ollama_chat/llama3.1": {
        "supports_function_calling": True
    },
})
```

### Tool calling proxy config
In your `config.yaml`, signal function calling support:

```yaml
model_list:
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama_chat/llama3.1"
      keep_alive: "8m"
    model_info:
      supports_function_calling: true
```

### Code example
```python
from litellm import completion

tools = [
  {
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get the current weather in a given location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {"type": "string", "description": "City and state"},
          "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
      },
    }
  }
]

messages = [{"role": "user", "content": "What's the weather like in Boston today?"}]

response = completion(
  model="ollama_chat/llama3.1",
  messages=messages,
  tools=tools
)
```

> **Models known to support tool calling:** Llama 3.1, Mistral, Qwen 2.5, and newer models. For other models, LiteLLM falls back to JSON mode automatically.

---

## 5. Stream Options

### Basic streaming with LiteLLM SDK
```python
from litellm import completion

response = completion(
    model="ollama/llama2",
    messages=[{"content": "Hello, how are you?", "role": "user"}],
    api_base="http://localhost:11434",
    stream=True,
)

for chunk in response:
    print(chunk)
```

### Streaming via OpenAI-compatible client
```python
import openai

openai.api_base = "http://0.0.0.0:4000"
openai.api_key = "temp-key"

response = openai.chat.completions.create(
    model="ollama/llama2",
    messages=[{"role": "user", "content": "test request"}],
    stream=True
)

for chunk in response:
    print(f'LiteLLM: streaming response from proxy {chunk}')
```

### Streaming via LiteLLM Proxy
```python
response = litellm.completion(
    model="litellm_proxy/llama-3.1",
    messages=[{"role": "user", "content": "hello from litellm"}],
    api_base="http://localhost:4000",
    api_key="your-proxy-api-key",
    stream=True
)

for chunk in response:
    if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

Key points:
- Set `stream=True` in the completion call
- Iterate over the response for chunks
- When using the proxy's OpenAI-compatible endpoint, check `chunk.choices[0].delta.content`

---

## 6. Multiple Ollama Models in Same LiteLLM Config

### Proxy config.yaml — multiple Ollama models
```yaml
model_list:
  - model_name: "llama3.1"               
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"

  - model_name: "deepseek-r1"               
    litellm_params:
      model: "ollama_chat/deepseek-r1"
      api_base: "http://localhost:11434"

  - model_name: "codellama"
    litellm_params:
      model: "ollama/codellama"
      api_base: "http://localhost:11434"
```

### Mixing Ollama with other providers
```yaml
model_list:
  # Ollama models
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"

  - model_name: "mistral-local"
    litellm_params:
      model: "ollama/mistral"
      api_base: "http://localhost:11434"

  # Cloud models
  - model_name: "gpt-4"
    litellm_params:
      model: "openai/gpt-4"
      api_key: os.environ/OPENAI_API_KEY
```

### Starting proxy with a single Ollama model (no config file)
```bash
litellm --model ollama/codellama --temperature 0.3 --max_tokens 2048
```

### Key config fields
| Field | Description |
|---|---|
| `model_name` | Alias used by clients to refer to this model |
| `litellm_params.model` | Actual provider/model path (`ollama/...` or `ollama_chat/...`) |
| `litellm_params.api_base` | Ollama server URL |
| `litellm_params.keep_alive` | How long the model stays loaded in memory |
| `model_info.supports_function_calling` | Signal tool calling capability |

---

## 7. Common Errors and Fixes

### "Model not found" / 404
```
{"detail": {"error": "Model 'gpt-3.5-turbo' not found in router", ...}}
```
**Causes & fixes:**
- **Wrong model name** — model name in the request must match `model_name` in config, not the Ollama model name
- **Model not in config** — verify with: `curl http://localhost:4000/v1/models -H "Authorization: Bearer <key>"`
- **Ollama model not pulled** — run `ollama pull <model-name>` first

### Connection refused to Ollama
```
Connection refused: http://localhost:11434
```
**Causes & fixes:**
- **Ollama not running** — start Ollama with `ollama serve` or as a service
- **Wrong `api_base` in Docker** — on Linux use `http://host.docker.internal:11434` or host IP; for Docker networking use container name
- **Port mismatch** — verify Ollama is on port 11434 (default)

### Unsupported parameters error
When OpenAI-specific params (e.g., `response_format`, `stop_sequences`) are sent to Ollama models.

**Fix 1 — Drop per request:**
```python
litellm.drop_params = True
# or pass directly:
completion(..., drop_params=True)
```

**Fix 2 — Drop globally in proxy config:**
```yaml
litellm_settings:
    drop_params: true
```

**Fix 3 — Drop via CLI flag:**
```bash
litellm --model ollama/codellama --drop_params
```

**Fix 4 — Drop specific params in config:**
```yaml
litellm_params:
  model: "ollama/codellama"
  additional_drop_params: ["reasoningSummary"]
```

### Timeout errors
```
Timeout error — request took too long
```
**Causes & fixes:**
- **Model still loading** — Ollama loads models on first request; first call is slow; set `keep_alive` to keep loaded
- **Underpowered hardware** — reduce context length, use smaller models
- **Network issues** — check connectivity between LiteLLM and Ollama

### Function calling not working
- **Wrong model prefix** — tool calling requires `ollama_chat/`, not `ollama/`
- **Model doesn't support native tool calling** — LiteLLM falls back to JSON mode automatically; or register model with `supports_function_calling: true`

### General Litellm Proxy errors
```bash
# Check proxy logs for detailed errors
litellm --model ollama/codellama --detailed_debug
```

---

## Quick Reference

| Task | Correct Approach |
|---|---|
| Basic completion | `model="ollama/llama3"`, `api_base="http://localhost:11434"` |
| Chat completion | `model="ollama_chat/llama3.1"` |
| Tool calling | `model="ollama_chat/llama3.1"`, pass `tools=`, optionally register model |
| Streaming | Add `stream=True`, iterate over response |
| Keep model loaded | Add `keep_alive: "30m"` or `keep_alive: "-1"` to config |
| Drop unsupported params | `litellm.drop_params = True` or `--drop_params` flag |
| Test connectivity | `curl http://localhost:11434/api/tags` (Ollama), `curl http://localhost:4000/v1/models` (proxy) |

---

*Sources: Context7 API querying docs.litellm.ai (latest as of 2026-05-08)*
