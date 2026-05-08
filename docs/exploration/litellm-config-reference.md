# LiteLLM Proxy — Complete config.yaml Reference

> **Source:** Official LiteLLM docs (https://docs.litellm.ai/docs/proxy/configs)
> **Last fetched:** 2026-05-08 via Context7

---

## Top-Level Structure

```yaml
model_list:              # Required: list of model definitions
router_settings:         # Optional: router behavioral tuning
litellm_settings:        # Optional: global LiteLLM module settings
general_settings:        # Optional: proxy server config
environment_variables:   # Optional: env vars injected at startup
```

---

## 1. `model_list` — Model Definitions

Each entry maps an alias (`model_name`) to a provider-specific model with credentials.

```yaml
model_list:
  - model_name: "my-alias"             # ← The name clients use in their requests
    litellm_params:
      model: "provider/model-name"     # ← Provider prefix + model name
      api_key: "os.environ/MY_KEY"     # ← Reads from env var (LiteLLM syntax)
      api_base: "https://..."          # ← Custom endpoint (optional)
      rpm: 6                           # ← Rate limit: requests per minute (optional)
      tpm: 40000                       # ← Rate limit: tokens per minute (optional)
      api_version: "2025-01-01-preview" # ← For Azure (optional)
      timeout: 30                      # ← Request timeout in sec (optional)
      stream_timeout: 30               # ← Streaming timeout in sec (optional)
      max_retries: 3                   # ← Per-model retries (optional)
      use_chat_completions_api: true   # ← Force chat completions API (optional)
```

### Provider Prefixes (the `model:` format)

| Provider | Example | Notes |
|----------|---------|-------|
| **OpenAI** | `openai/gpt-4o` | Standard OpenAI API |
| **OpenAI-compatible** | `openai/my-model` | Use with `api_base` for custom endpoints |
| **Ollama** | `ollama/llama3.1` | Local via `api_base: http://localhost:11434` |
| **Anthropic** | `anthropic/claude-3-5-sonnet-latest` | |
| **Azure** | `azure/gpt-4-deployment` | Also set `api_version` |
| **Gemini** | `gemini/gemini-2.0-flash` | Or `vertex_ai/...` |
| **Bedrock** | `bedrock/converse_like/...` | |
| **xAI** | `xai/grok-3` | |
| **Custom** | `openai/<name>` | Any OpenAI-compatible endpoint |

### Example: Multiple Ollama Models

```yaml
model_list:
  - model_name: "llama3"
    litellm_params:
      model: "ollama/llama3"
      api_base: "http://localhost:11434"

  - model_name: "codellama"
    litellm_params:
      model: "ollama/codellama"
      api_base: "http://localhost:11434"

  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"
```

### Example: OpenAI-Compatible Upstream (e.g. DeepSeek, OpenRouter, Together)

Use the `openai/` prefix with a custom `api_base`:

```yaml
model_list:
  - model_name: "deepseek-chat"
    litellm_params:
      model: "openai/deepseek-chat"           # ← openai/ prefix + your model name
      api_key: "os.environ/DEEPSEEK_API_KEY"   # ← Your API key
      api_base: "https://api.deepseek.com/v1"  # ← Custom base URL

  - model_name: "deepseek-reasoner"
    litellm_params:
      model: "openai/deepseek-reasoner"
      api_key: "os.environ/DEEPSEEK_API_KEY"
      api_base: "https://api.deepseek.com/v1"

  - model_name: "my-local-model"
    litellm_params:
      model: "openai/my-custom-model"
      api_key: "fake-key"
      api_base: "http://localhost:8080/v1"
```

> **Key insight:** The `openai/` prefix tells LiteLLM to use the OpenAI-compatible SDK.  
> The string after `/` is the `model` name sent in the upstream request body.  
> Your `api_key` and `api_base` are used for the connection.

### Example: Load Balancing (Same Model, Multiple Deployments)

```yaml
model_list:
  - model_name: "gpt-4"
    litellm_params:
      model: "openai/gpt-4"
      api_key: "os.environ/OPENAI_API_KEY"
    rpm: 500

  - model_name: "gpt-4"                  # ← Same model_name = load balanced group
    litellm_params:
      model: "azure/gpt-4"
      api_key: "os.environ/AZURE_API_KEY"
      api_base: "os.environ/AZURE_API_BASE"
      api_version: "2025-01-01-preview"
    rpm: 800
```

---

## 2. `router_settings` — Routing Behavior

Controls how the proxy routes, retries, fails over, and cools down deployments.

```yaml
router_settings:
  # --- Routing Strategy ---
  routing_strategy: "simple-shuffle"
  # Options: "simple-shuffle" (default), "least-busy",
  #          "usage-based-routing", "latency-based-routing"
  # "simple-shuffle" is RECOMMENDED for best performance.

  # --- Model Group Aliasing ---
  model_group_alias: {"gpt-4": "gpt-3.5-turbo"}
  # Requests for "gpt-4" will be routed to models named "gpt-3.5-turbo"

  # --- Retries ---
  num_retries: 2               # Number of retries on failure
  retry_after: 5               # Min seconds to wait before retry (optional)

  # --- Timeout ---
  timeout: 30                  # Global request timeout in seconds

  # --- Cooldowns ---
  allowed_fails: 3             # Cooldown model if it fails > N calls in a minute
  cooldown_time: 30            # Seconds to cooldown (must be > health_check_interval)
  disable_cooldowns: false     # Set true to disable all cooldowns

  # --- Fallbacks ---
  fallbacks:
    - {"gpt-3.5-turbo": ["gpt-4"]}
    # If gpt-3.5-turbo fails, fall back to gpt-4

  content_policy_fallbacks:
    - {"claude-2": ["my-fallback-model"]}
    # Only triggered on content policy violations

  context_window_fallbacks:
    - {"claude-2": ["my-fallback-model"]}
    # Only triggered on context window exceeded errors

  # --- Preserved Call Checks ---
  enable_pre_call_checks: true
  # Before making a call, check if the request fits within the model's context window

  # --- Tag-Based Routing ---
  enable_tag_filtering: false
  tag_filtering_match_any: true
  # true: match if deployment has ANY requested tag
  # false: match only if deployment has ALL requested tags

  # --- Redis (for multi-instance state) ---
  redis_host: "localhost"
  redis_port: 6379
  redis_password: "your-password"

  # --- Retry Policy (per error type) ---
  retry_policy:
    BadRequestErrorRetries: 3
    AuthenticationErrorRetries: 3
    TimeoutErrorRetries: 3
    RateLimitErrorRetries: 3
    ContentPolicyViolationErrorRetries: 4
    InternalServerErrorRetries: 4

  # --- Allowed Fails Policy (per error type) ---
  allowed_fails_policy:
    BadRequestErrorAllowedFails: 1000
    AuthenticationErrorAllowedFails: 10
    TimeoutErrorAllowedFails: 12
    RateLimitErrorAllowedFails: 10000
    ContentPolicyViolationErrorAllowedFails: 15
    InternalServerErrorAllowedFails: 20
```

---

## 3. `litellm_settings` — Global Module Settings

These control the LiteLLM Python module behavior (caching, callbacks, verbosity, etc.).

```yaml
litellm_settings:
  # --- Parameter Handling ---
  drop_params: true
  # Automatically drop unsupported parameters for a given model/provider.
  # CRITICAL when using the same model name string across different providers.

  set_verbose: false
  # Enable verbose/debug logging from LiteLLM.

  request_timeout: 600
  # Default request timeout in seconds for all models.

  # --- Callbacks / Observability ---
  success_callback: ["langfuse", "helicone"]
  # Called on successful completions. Common: langfuse, helicone, deepeval, newrelic

  failure_callback: ["sentry", "deepeval"]
  # Called on failed completions. Common: sentry, deepeval, langfuse

  callbacks: "custom_callbacks.proxy_handler_instance"
  # Custom Python callback path (module.ClassName or module.instance)

  service_callbacks: ["datadog", "prometheus"]
  # For service-level monitoring (Redis, PostgreSQL health)

  log_raw_request_response: true
  # Log the full raw request/response bodies (useful for debugging).

  # --- Caching ---
  cache: true
  cache_params:
    type: "redis"                         # "redis" or "local" (default: local)
    host: "localhost"
    port: 6379
    password: "your-password"
    namespace: "litellm.caching.caching"  # Optional: custom Redis key prefix
    mode: "default_off"                   # Optional: require explicit opt-in
    # mode options: "default_off" (opt-in) or omit (default-on)

  enable_caching_on_provider_specific_optional_params: true
  # Include provider-specific params in cache key computation.

  # --- Headers ---
  forward_client_headers_to_llm_api: ["anthropic-version"]
  # Forward specific client headers to the upstream LLM API.

  # --- Security ---
  ssl_ecdh_curve: "X25519"
  # ECDH curve for SSL/TLS key exchange.

  ssl_certificate: "/path/to/certificate.pem"
  # Client-side certificate path.

  # --- Cost Tracking ---
  disable_end_user_cost_tracking: false
  disable_end_user_cost_tracking_prometheus_only: false

  # --- Retries (alternative to router_settings.num_retries) ---
  num_retries: 2
```

---

## 4. `general_settings` — Proxy Server Configuration

```yaml
general_settings:
  # --- Authentication ---
  master_key: "sk-1234"
  # Admin key for generating virtual keys. Must start with "sk-".
  # Also accepts env var: LITELLM_MASTER_KEY

  # --- Database (required for virtual keys & persistent state) ---
  database_url: "postgresql://user:password@localhost:5432/litellm"
  # Also accepts env var: DATABASE_URL

  # --- UI Admin Credentials ---
  UI_USERNAME: "admin"
  UI_PASSWORD: "your-strong-password"

  # --- Global Budget ---
  max_budget: 0.0              # Float: max budget in USD (0 = no spend)
  budget_duration: "30d"       # Reset frequency: 30s, 30m, 30h, 30d

  # --- Health Checks ---
  background_health_checks: true
  use_shared_health_check: true    # Share state across proxy pods (requires Redis)
  health_check_interval: 30        # Seconds between checks

  # --- Alerting ---
  alerting: ["slack"]                              # Alerting channels
  alerting_threshold: 300                          # Alert if request hangs 5min+
  spend_report_frequency: "1d"                     # How often to send spend reports

  alerting_args:
    daily_report_frequency: 43200     # 12h in seconds
    report_check_interval: 3600       # 1h in seconds
    budget_alert_ttl: 86400           # 24h in seconds
    outage_alert_ttl: 60              # 1min in seconds
    region_outage_alert_ttl: 60       # 1min in seconds
    minor_outage_alert_threshold: 5
    major_outage_alert_threshold: 10
    max_outage_alert_list_size: 1000
    log_to_console: false

  # --- Secret Managers ---
  key_management_system: "google_secret_manager"
  # Options: "google_secret_manager", "azure_key_vault", "aws_secret_manager"

  # --- Request Validation ---
  reject_clientside_metadata_tags: true
  enforce_user_param: true

  # --- Pass-Through Endpoints ---
  pass_through_endpoints:
    - path: "/v1/messages"
      target: "my_module.MyAdapter"
```

---

## 5. `environment_variables` — Startup Injection

Define environment variables that get set when the proxy starts.
Useful for secrets that are consumed as `os.environ/VAR_NAME` in model configs.

```yaml
environment_variables:
  OPENAI_API_KEY: "sk-..."
  ANTHROPIC_API_KEY: "sk-ant-..."
  DEEPSEEK_API_KEY: "sk-..."
  HELICONE_API_KEY: "your-helicone-key"
  DATABASE_URL: "postgresql://user:pass@localhost:5432/litellm"
  LITELLM_MASTER_KEY: "sk-1234"
```

> **Note:** Variables listed here are injected at proxy startup.  
> You can also set them externally via `export VAR=value` or a `.env` file.

---

## 6. Environment Variable Substitution

LiteLLM supports **two** mechanisms:

### 6a. `os.environ/VAR_NAME` syntax (in YAML values)

This is LiteLLM's own syntax for referencing env vars INSIDE the config file:

```yaml
litellm_params:
  api_key: "os.environ/OPENAI_API_KEY"    # ← LiteLLM reads this at runtime
  api_base: "os.environ/MY_API_BASE"
```

The value `os.environ/VAR_NAME` tells LiteLLM to do `os.getenv("VAR_NAME")`.

### 6b. Shell environment variables (at proxy runtime)

Set before starting the proxy:

```bash
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://..."
export LITELLM_MASTER_KEY="sk-1234"

litellm --config /path/to/config.yaml
```

LiteLLM also reads these well-known env vars automatically:

| Env Var | Maps To |
|---------|---------|
| `LITELLM_MASTER_KEY` | `general_settings.master_key` |
| `DATABASE_URL` | `general_settings.database_url` |
| `OPENAI_API_KEY` | OpenAI default |
| `ANTHROPIC_API_KEY` | Anthropic default |
| `OPENAI_BASE_URL` | Custom base URL for OpenAI SDK |

---

## 7. Complete Working Example

```yaml
# =============================================================================
# LiteLLM Proxy — Complete Working config.yaml
# =============================================================================
# Start with:  litellm --config config.yaml
# Proxy runs on: http://0.0.0.0:4000
# =============================================================================

model_list:
  # --- Ollama local models ---
  - model_name: "llama3"
    litellm_params:
      model: "ollama/llama3"
      api_base: "http://localhost:11434"
      rpm: 30

  - model_name: "codellama"
    litellm_params:
      model: "ollama/codellama"
      api_base: "http://localhost:11434"
      rpm: 30

  # --- OpenAI-compatible upstream (e.g. DeepSeek) ---
  - model_name: "deepseek-chat"
    litellm_params:
      model: "openai/deepseek-chat"
      api_key: "os.environ/DEEPSEEK_API_KEY"
      api_base: "https://api.deepseek.com/v1"
      rpm: 1000

  - model_name: "deepseek-reasoner"
    litellm_params:
      model: "openai/deepseek-reasoner"
      api_key: "os.environ/DEEPSEEK_API_KEY"
      api_base: "https://api.deepseek.com/v1"
      rpm: 500

  # --- OpenAI models ---
  - model_name: "gpt-4o"
    litellm_params:
      model: "openai/gpt-4o"
      api_key: "os.environ/OPENAI_API_KEY"
      rpm: 5000

# --- Routing behavior ---
router_settings:
  routing_strategy: "simple-shuffle"
  num_retries: 2
  timeout: 30
  allowed_fails: 3
  cooldown_time: 30
  fallbacks:
    - {"deepseek-chat": ["gpt-4o"]}
  retry_policy:
    BadRequestErrorRetries: 0
    AuthenticationErrorRetries: 1
    TimeoutErrorRetries: 3
    RateLimitErrorRetries: 3
    InternalServerErrorRetries: 2
  allowed_fails_policy:
    RateLimitErrorAllowedFails: 100
    TimeoutErrorAllowedFails: 12
    InternalServerErrorAllowedFails: 10

# --- Global LiteLLM module settings ---
litellm_settings:
  drop_params: true
  set_verbose: false
  request_timeout: 600
  cache: true
  cache_params:
    type: "local"
  success_callback: ["langfuse"]
  failure_callback: ["sentry"]

# --- Proxy server settings ---
general_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"
  database_url: "os.environ/DATABASE_URL"
  background_health_checks: true
  health_check_interval: 30
  alerting: ["slack"]
  alerting_threshold: 300

# --- Environment variables injected at startup ---
environment_variables:
  DEEPSEEK_API_KEY: "${DEEPSEEK_API_KEY}"    # ← read from shell env at startup
  OPENAI_API_KEY: "${OPENAI_API_KEY}"
  LITELLM_MASTER_KEY: "${LITELLM_MASTER_KEY}"
  DATABASE_URL: "${DATABASE_URL}"
```

> **Note on `${VAR}` syntax:** The `environment_variables` section uses standard YAML
> string values. If you write `${VAR_NAME}`, the shell expands it before YAML parsing
> (if you use `litellm --config`). The `os.environ/VAR_NAME` syntax is LiteLLM's own
> runtime lookup mechanism used inside `litellm_params`.

---

## Key Takeaways

1. **Provider prefix is essential** — `ollama/`, `openai/`, `anthropic/`, `azure/`, etc.
2. **Custom OpenAI-compatible endpoints** → use `openai/<model>` with `api_base`
3. **Secret management** → use `os.environ/VAR_NAME` in YAML values, NOT `${VAR}`
4. **`drop_params: true`** is critical when using models across providers
5. **`router_settings`** > `litellm_settings` for overlapping keys (router_settings wins)
6. **`master_key`** must start with `sk-` (required for virtual keys)
7. **`database_url`** is required for persistent virtual keys and user management
