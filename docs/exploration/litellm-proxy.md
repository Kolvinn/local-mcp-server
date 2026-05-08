# LiteLLM Proxy — Exploration Report

> Source: Context7 API queries against `/websites/litellm_ai` (official docs, 9046 snippets, trust score 9/10) and `/berriai/litellm` (GitHub repo, 956 snippets, trust score 7.7/10).
> Date: 2026-05-08

---

## Summary (3 bullets)

1. **LiteLLM is a strong unified routing layer for LangChain/LangGraph** — it exposes a single OpenAI-compatible API (`/v1/chat/completions`, `/v1/embeddings`) that transparently proxies to Ollama, OpenAI, Anthropic, vLLM, and 100+ other providers. The Proxy Server (`litellm --config config.yaml`) runs locally on `0.0.0.0:4000` and can be pointed at local Ollama instances, making it an ideal intermediary between LangChain agents and heterogeneous model backends.

2. **Resilience is deeply built-in** — LiteLLM offers per-exception retry policies (`RetryPolicy`), configurable cooldowns/circuit breakers (`allowed_fails`, `cooldown_time`, `AllowedFailsPolicy`), model fallback chains (declared in `config.yaml` or via the Python `Router`), and multiple routing strategies (`simple-shuffle`, `least-busy`, `usage-based-routing`, `latency-based-routing`, `cost-based-routing`, and the newer `adaptive_router`/`complexity_router`).

3. **Streaming works across providers with normalized OpenAI-format chunks** — `stream=True` is supported for Ollama and all major providers. LiteLLM normalizes streaming chunks to `choices[0].delta` (OpenAI format). For providers that don't natively stream (e.g. Sagemaker), LiteLLM simulates streaming by chunking the response string. Async equivalents (`acompletion`) are available for non-blocking use.

---

## Key Findings

### 1. Proxy Server — Local Ollama Backend

**How to run:**
```bash
# Simplest: direct model
litellm --model ollama/codellama --temperature 0.3 --max_tokens 2048

# With config file (recommended for multi-model):
litellm --config /path/to/config.yaml
```

**Config for Ollama backend:**
```yaml
model_list:
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"     # default Ollama port
      keep_alive: "8m"                       # optional: override Ollama keep_alive
    model_info:
      supports_function_calling: true        # Ollama supports tool use
```

The proxy listens on `http://0.0.0.0:4000` by default and accepts standard OpenAI API calls. Authentication is enforced via `general_settings.master_key`.

---

### 2. Unified OpenAI-Compatible API

- LiteLLM maps every provider to OpenAI's request/response shapes.
- **Completion:** `litellm.completion(model="ollama/llama2", messages=[...])` returns an `OpenAIObject` with `choices[0].message.content`.
- **Custom OpenAI-compatible endpoints:** Use `openai/` prefix + `api_base` to talk to any OpenAI-compatible server (e.g., vLLM, TGI, local proxies).
- The proxy itself is an OpenAI-compatible server — any SDK that speaks OpenAI can talk to it.

**Python SDK vs Proxy:**
- **Python SDK (`Router` class):** Embed LiteLLM directly in your app; use `Router.completion()` / `Router.acompletion()`.
- **Proxy Server:** Deploy as a sidecar/container; any HTTP client talks to it via standard OpenAI API.

---

### 3. Retry Logic, Fallbacks, Rate Limiting, Circuit Breaker

**RetryPolicy — per-exception retry counts:**
```python
retry_policy = RetryPolicy(
    ContentPolicyViolationErrorRetries=3,
    AuthenticationErrorRetries=0,
    RateLimitErrorRetries=3,
    TimeoutErrorRetries=3,
    InternalServerErrorRetries=4,
)
```

**AllowedFailsPolicy — circuit breaker per error type:**
```yaml
allowed_fails_policy:
  RateLimitErrorAllowedFails: 10000      # Allow 10k rate limits before cooldown
  InternalServerErrorAllowedFails: 20     # 20 server errors → cooldown
  ContentPolicyViolationErrorAllowedFails: 15
```

**Cooldown:**
```yaml
router_settings:
  allowed_fails: 3            # cooldown if >3 fails per minute
  cooldown_time: 30           # seconds
```

**Model fallbacks (in config.yaml):**
```yaml
router_settings:
  fallbacks: [{"gpt-4": ["azure/gpt-4", "ollama/llama3.1"]}]
```

**Content policy fallbacks (separate from error fallbacks):**
```yaml
router_settings:
  content_policy_fallbacks: [{"claude-2": ["my-fallback-model"]}]
```

**Manual fallback loop (SDK):**
LiteLLM docs include a reference implementation that tries models in order, tracks rate-limited models with a 60s cooldown, and times out after 45 seconds.

---

### 4. Multi-Model Routing (Ollama + Others)

**Multiple Ollama models as distinct endpoints:**
```yaml
model_list:
  - model_name: "ollama-llama3"
    litellm_params:
      model: "ollama/llama3"
      api_base: "http://localhost:11434"
  - model_name: "ollama-codellama"
    litellm_params:
      model: "ollama/codellama"
      api_base: "http://localhost:11434"
  - model_name: "ollama-mistral"
    litellm_params:
      model: "ollama/mistral"
      api_base: "http://localhost:11434"
```

Clients call `model="ollama-llama3"` etc. via the OpenAI API.

**Routing strategies available:**
| Strategy | Description |
|---|---|
| `simple-shuffle` | Round-robin across deployments with same `model_name` |
| `least-busy` | Picks deployment with fewest active requests |
| `usage-based-routing` | Routes based on TPM/RPM capacity (requires Redis) |
| `latency-based-routing` | Routes to lowest-latency deployment |
| `cost-based-routing` | Routes to cheapest deployment |
| `adaptive_router` | Routes based on quality/cost weights and model strengths |
| `complexity_router` | Routes based on query complexity (SIMPLE/MEDIUM/COMPLEX/REASONING tiers) |

**Model group aliasing:**
```yaml
router_settings:
  model_group_alias: {"gpt-4": "gpt-3.5-turbo"}  # alias requests
```

This means LangChain can call `model="gpt-4"` and LiteLLM routes it to whatever Ollama model is configured under that alias.

---

### 5. Streaming Support and Response Normalization

- **All providers:** `stream=True` is universally supported.
- **Response shape:** Every chunk follows OpenAI format — `chunk.choices[0].delta.content` — regardless of backend provider.
- **Async streaming:**
  ```python
  response = await litellm.acompletion(model="ollama/llama2", messages=[...], stream=True)
  async for chunk in response:
      print(chunk.choices[0].delta.content)
  ```
- **Simulated streaming:** For providers that don't support native streaming (e.g., Sagemaker), LiteLLM simulates by splitting the response into chunks.
- **Streaming + usage tracking:** Pass `stream_options={"include_usage": True}` to get token usage in the final chunk (supported where the provider exposes it).
- **Consistent output:** `litellm.completion()` always returns an `OpenAIObject`-style response, so LangChain's `ChatOpenAI(model="...", base_url="http://localhost:4000/v1")` works seamlessly.

---

### 6. Embeddings and Provider-Specific Quirks

**Usage:**
```python
from litellm import embedding
response = embedding(
    model="ollama/nomic-embed-text",   # or "openai/text-embedding-3-small", "jina_ai/jina-embeddings-v3", etc.
    input=["your text here"],
)
```

**Provider-specific quirks found:**
- **vLLM embeddings incident (Feb 2026):** vLLM rejects `encoding_format=None` being explicitly passed. LiteLLM had a ~3-hour outage for vLLM embeddings until the patch shipped. **Fix applied:** LiteLLM now filters out `None` and empty string optional params before sending to vLLM.
- **Jina AI:** Accepts extra provider-specific kwargs (e.g., `dimensions=1536`, `my_custom_param="value"`) which are forwarded directly.
- **Nvidia NIM:** Requires `nvidia_nim/` prefix; supports `input_type` and `truncate` as optional params.
- **Perplexity:** Uses `perplexity/` prefix; supports `dimensions` param.
- **Ollama embeddings:** Use `ollama/<embedding-model-name>` format; works out of the box with local Ollama.
- **General pattern:** Extra kwargs are forwarded to the provider's native API where supported. If a provider doesn't support a parameter, it may cause errors (as seen with vLLM).

---

## Assessment: LiteLLM as Unified Routing Layer

### Strengths for this use case:
1. **Zero-code provider switching** — LangChain talks OpenAI format to LiteLLM proxy; LiteLLM handles all provider translation.
2. **Ollama-native** — First-class Ollama support with `ollama/` prefix, keep_alive, function calling detection.
3. **Rich routing** — Can route by cost, latency, usage-capacity, or query complexity; supports fallbacks and cooldowns.
4. **Production-grade resilience** — Per-exception retries, circuit breakers, cooldowns, content-policy fallbacks.
5. **Streaming normalized** — No special handling needed per provider.
6. **Embeddings work** — Both proxy and SDK support embeddings; provider quirks (vLLM) are patched.

### Considerations:
1. **Redis dependency** for `usage-based-routing` across multiple proxy instances (single-instance doesn't need Redis).
2. **Provider-specific params** — Some providers have quirks (e.g., vLLM's `encoding_format` rejection). LiteLLM is actively patching these.
3. **Overhead** — Running the proxy adds one network hop. For latency-sensitive applications, consider the Python SDK `Router` instead (in-process).
4. **Version stability** — LiteLLM ships nightly releases; pin to a stable version (`v1.81.9-stable` or `v1.83.3-stable`).

### Recommendation:
LiteLLM proxy is well-suited as the routing layer between LangChain/LangGraph and Ollama + opencode upstream models. Deploy as a sidecar with a pinned stable version, configure `config.yaml` with all desired Ollama models, and point LangChain's `ChatOpenAI(base_url="http://localhost:4000/v1")` at it. Use the Python `Router` class if you need in-process routing without the network hop.
