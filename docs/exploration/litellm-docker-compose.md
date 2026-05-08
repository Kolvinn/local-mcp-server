# LiteLLM Docker Compose Setup — Complete Reference

**Generated:** 2026-05-08
**Source:** Context7 documentation for LiteLLM (`/berriai/litellm`)
**Repo:** https://github.com/berriai/litellm (branch: `litellm_internal_staging`)

---

## 1. Overview

LiteLLM is a lightweight proxy server that exposes all LLM APIs (OpenAI, Anthropic, Bedrock, Ollama, etc.) under the OpenAI-compatible format. This document provides a working `docker-compose.yml` and `litellm_config.yaml` for deploying LiteLLM with:

- PostgreSQL for persistence (spend logs, keys, model config)
- Prometheus for metrics
- Multiple Ollama models (running on the host)

---

## 2. Official docker-compose.yml (from LiteLLM repo)

Source: https://github.com/berriai/litellm/blob/litellm_internal_staging/docker-compose.yml

The official compose file defines three services:

- **litellm** — the proxy server (port 4000)
- **db** — PostgreSQL 16 (port 5432)  
- **prometheus** — metrics collection (port 9090)

---

## 3. Working docker-compose.yml (with Ollama host networking)

```yaml
version: "3.9"

services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: litellm_proxy
    restart: unless-stopped
    ports:
      - "4000:4000"
    volumes:
      # Mount config.yaml into the container — this is THE way to configure LiteLLM in Docker
      - ./litellm_config.yaml:/app/config.yaml
      # Optional: mount .env for API keys if not using os.environ/ in config
      - ./.env:/app/.env
    environment:
      # Database connection — use service name "db" for internal Docker networking
      DATABASE_URL: "postgresql://llmproxy:dbpassword9090@db:5432/litellm"
      STORE_MODEL_IN_DB: "True"
      # Master key for proxy admin — MUST be set
      LITELLM_MASTER_KEY: "sk-1234"
      # Pass host.docker.internal as an env var so config.yaml can use it via os.environ/
      OLLAMA_HOST: "host.docker.internal"
      # Extra proxy config
      LITELLM_HOST: "0.0.0.0"
      LITELLM_PORT: "4000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    # Health check — LiteLLM has a dedicated /health/liveliness endpoint
    healthcheck:
      test: [ "CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')\"" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # Extra hosts for Docker Desktop / Linux host access
    extra_hosts:
      - "host.docker.internal:host-gateway"
    # Network mode: bridge is default; use extra_hosts instead of network_mode: host
    # for cleaner port mapping. If you need host network (Linux without host.docker.internal):
    # network_mode: "host"
    # ports: []  # (remove ports when using host network)

  db:
    image: postgres:16
    restart: always
    container_name: litellm_db
    environment:
      POSTGRES_DB: litellm
      POSTGRES_USER: llmproxy
      POSTGRES_PASSWORD: dbpassword9090
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -d litellm -U llmproxy" ]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

  prometheus:
    image: prom/prometheus
    container_name: litellm_prometheus
    restart: unless-stopped
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=15d"

volumes:
  prometheus_data:
    driver: local
  postgres_data:
    name: litellm_postgres_data
```

### Key Points

| Setting | Purpose |
|---|---|
| `volumes: ./litellm_config.yaml:/app/config.yaml` | Mounts your local config; LiteLLM reads `/app/config.yaml` at startup |
| `extra_hosts: host.docker.internal:host-gateway` | On Linux, maps `host.docker.internal` → host machine so Ollama on the host is reachable |
| `depends_on: db: condition: service_healthy` | Waits for PostgreSQL to be ready before starting LiteLLM |
| `DATABASE_URL` | Points to the `db` service via Docker internal DNS |
| `LITELLM_MASTER_KEY` | Required for signing and validating proxy tokens |

---

## 4. litellm_config.yaml (with multiple Ollama models)

```yaml
# =============================================================================
# LiteLLM Proxy Configuration — Multiple Ollama Models
# =============================================================================
# Place this at ./litellm_config.yaml alongside docker-compose.yml
# Mounted into the container at /app/config.yaml

model_list:
  # ── Ollama Models (running on host machine) ──────────────────────────────
  # Ollama host is reachable via host.docker.internal:11434
  # The `api_base` uses the OLLAMA_HOST env var defined in docker-compose.yml

  - model_name: llama3.2
    litellm_params:
      model: ollama/llama3.2
      api_base: "http://host.docker.internal:11434"
      max_tokens: 4096
      request_timeout: 120

  - model_name: llama3.1
    litellm_params:
      model: ollama/llama3.1
      api_base: "http://host.docker.internal:11434"
      max_tokens: 4096
      request_timeout: 120

  - model_name: mistral
    litellm_params:
      model: ollama/mistral
      api_base: "http://host.docker.internal:11434"
      max_tokens: 4096
      request_timeout: 120

  - model_name: codellama
    litellm_params:
      model: ollama/codellama
      api_base: "http://host.docker.internal:11434"
      max_tokens: 8192
      request_timeout: 180

  - model_name: mixtral
    litellm_params:
      model: ollama/mixtral:8x7b
      api_base: "http://host.docker.internal:11434"
      max_tokens: 8192
      request_timeout: 180

  - model_name: deepseek-coder
    litellm_params:
      model: ollama/deepseek-coder
      api_base: "http://host.docker.internal:11434"
      max_tokens: 8192
      request_timeout: 180

  - model_name: qwen2.5
    litellm_params:
      model: ollama/qwen2.5
      api_base: "http://host.docker.internal:11434"
      max_tokens: 4096
      request_timeout: 120

  # ── OpenAI models (example: add your API key in .env) ────────────────────
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  # ── Anthropic models (example) ───────────────────────────────────────────
  - model_name: claude-sonnet-4
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: claude-haiku
    litellm_params:
      model: anthropic/claude-3-5-haiku-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

# ── Router Settings ──────────────────────────────────────────────────────
router_settings:
  routing_strategy: usage-based                   # or: simple-shuffle, latency-based, cost-based
  num_retries: 2
  allowed_fails: 1
  cooldown_time: 30
  enable_pre_call_checks: true

# ── LiteLLM-Specific Settings ────────────────────────────────────────────
litellm_settings:
  drop_params: true                                # Drop unsupported params instead of erroring
  set_verbose: false                               # Set to true for debug logging
  request_timeout: 600                             # Global request timeout in seconds
  callbacks: []                                    # e.g., ["langfuse", "s3", "gcs"]

# ── General Proxy Settings ───────────────────────────────────────────────
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY        # Required — references the env var
  database_url: os.environ/DATABASE_URL            # Required for persistence
  store_model_in_db: os.environ/STORE_MODEL_IN_DB  # Allow adding models via UI/API
  otel: false                                      # OpenTelemetry tracing
  alerting: []                                     # e.g., ["slack", "sentry"]
  proxy_log_to_athena: false
  # Allowed origins for CORS (if accessing from browser)
  allowed_origins: ["*"]
```

---

## 5. .env File

```bash
# =============================================================================
# LiteLLM Docker Environment Variables
# =============================================================================
# Place at ./.env alongside docker-compose.yml
# This file is read by both Docker Compose (env_file) and the config.yaml (os.environ/)

# ── Required ──────────────────────────────────────────────────────────────
LITELLM_MASTER_KEY=sk-1234
DATABASE_URL=postgresql://llmproxy:dbpassword9090@db:5432/litellm
STORE_MODEL_IN_DB=True

# ── API Keys (add as needed; referenced via os.environ/ in config.yaml) ──
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
# AZURE_API_KEY=...
# COHERE_API_KEY=...
# TOGETHERAI_API_KEY=...

# ── Ollama Host (injected into container for reference) ───────────────────
# On macOS/Windows Docker Desktop, host.docker.internal resolves automatically.
# On Linux, the extra_hosts: in docker-compose.yml makes it work.
OLLAMA_HOST=host.docker.internal
```

---

## 6. Environment Variable Reference

| Variable | Required | Description |
|---|---|---|
| `LITELLM_MASTER_KEY` | **Yes** | Master key for proxy admin — used to sign and validate API tokens |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string (`postgresql://user:pass@host:port/db`) |
| `STORE_MODEL_IN_DB` | No | When `True`, models can be added/removed via the proxy UI/API (persisted in DB) |
| `LITELLM_HOST` | No | Host to bind the proxy server to (default: `0.0.0.0`) |
| `LITELLM_PORT` | No | Port to listen on (default: `4000`) |
| `OPENAI_API_KEY` | * | Your OpenAI API key |
| `ANTHROPIC_API_KEY` | * | Your Anthropic API key |
| `AZURE_API_KEY` | * | Azure OpenAI API key |
| `TOGETHERAI_API_KEY` | * | TogetherAI API key |
| `AWS_ACCESS_KEY_ID` | * | AWS access key for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | * | AWS secret key for Bedrock |
| `AWS_REGION_NAME` | * | AWS region for Bedrock (e.g., `us-east-1`) |
| `OLLAMA_HOST` | * | Hostname/IP for Ollama server (use `host.docker.internal` for Docker-to-host) |

(* = required only if you configure those providers)

---

## 7. Exposing Ollama from Host to LiteLLM Container

### Problem
Ollama runs on the **host** at `localhost:11434`. The LiteLLM container cannot reach `localhost:11434` because that's the container's own loopback, not the host's.

### Solution A: extra_hosts (recommended, bridge network)

```yaml
services:
  litellm:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Then in `litellm_config.yaml`:
```yaml
litellm_params:
  model: ollama/llama3.2
  api_base: "http://host.docker.internal:11434"
```

- **macOS / Windows Docker Desktop**: `host.docker.internal` works out of the box.
- **Linux**: Requires the `extra_hosts` entry above (uses the `host-gateway` magic IP).

### Solution B: host network mode (Linux only)

```yaml
services:
  litellm:
    network_mode: "host"     # Container shares host network stack
    ports: []                # No port mapping needed
```

Then use `api_base: "http://localhost:11434"` in config. **Drawback:** All ports the container opens are exposed on the host; no port isolation.

### Verifying host.docker.internal works

```bash
# Inside the container
docker exec litellm_proxy sh -c "ping -c 2 host.docker.internal"
# Or test the Ollama endpoint
docker exec litellm_proxy sh -c "curl -s http://host.docker.internal:11434/api/tags"
```

---

## 8. Container Health Check & Startup Verification

### Built-in Health Check

The docker-compose.yml above includes a **healthcheck** for the `litellm` service:

```yaml
healthcheck:
  test: [ "CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')\"" ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health/liveliness` | Liveness check — server is alive and accepting requests |
| `GET /health` | General health — returns server status |
| `GET /health/readiness` | Readiness check — all dependencies (DB, etc.) are connected |

### Manual verification steps

```bash
# 1. Check container status
docker compose ps

# 2. View logs
docker compose logs litellm

# 3. Test the health endpoint
curl -s http://localhost:4000/health/liveliness

# 4. List available models (requires master key)
curl -s http://localhost:4000/models \
  -H "Authorization: Bearer sk-1234"

# 5. Run a chat completion test
curl -s http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-1234" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Say hello in 5 words."}]
  }'
```

### External Health Check Container (official LiteLLM image)

LiteLLM also provides a dedicated health-check Docker image:

```bash
docker run --rm \
  -e LITELLM_BASE_URL="http://host.docker.internal:4000" \
  -e LITELLM_API_KEY="sk-1234" \
  ghcr.io/berriai/litellm-health-check:latest
```

---

## 9. Startup Sequence

```
┌─────────┐     ┌──────────┐     ┌────────────┐
│  Docker  │────▶│ Postgres │────▶│  LiteLLM   │
│ Compose  │     │ (db)     │     │  Proxy     │
└─────────┘     └──────────┘     └────────────┘
     │               │                │
     │               │ healthcheck    │ healthcheck
     │               │ pg_isready     │ /health/liveliness
     ▼               ▼                ▼
  ┌─────────┐   ┌──────────┐   ┌────────────┐
  │Prometheus│   │postgres  │   │  Ready on  │
  │:9090     │   │_data vol │   │  :4000     │
  └─────────┘   └──────────┘   └────────────┘
```

1. `docker compose up -d --build` starts all services
2. PostgreSQL starts first; health check waits for `pg_isready`
3. LiteLLM starts only after PostgreSQL is healthy (`depends_on: db: condition: service_healthy`)
4. LiteLLM reads `/app/config.yaml` (your mounted file) and connects to the DB
5. Health check pings `/health/liveliness` every 30s after a 40s grace period

---

## 10. Quick Start Commands

```bash
# ── Start services ──
docker compose up -d

# ── View logs ──
docker compose logs -f litellm

# ── Stop services ──
docker compose down

# ── Full rebuild (clear volumes too) ──
docker compose down -v
docker compose up -d --build

# ── Shell into the container ──
docker exec -it litellm_proxy sh

# ── Test model via OpenAI-compatible API ──
curl http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-1234" \
  -d '{"model": "llama3.2", "messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## 11. File Layout

```
project/
├── docker-compose.yml        # Main compose file (above)
├── litellm_config.yaml       # LiteLLM proxy configuration (above)
├── .env                      # Environment variables / API keys
├── prometheus.yml            # Prometheus scrape config (optional)
└── docs/
    └── exploration/
        └── litellm-docker-compose.md   # This file
```

---

## 12. Sources

- Official docker-compose.yml: https://github.com/berriai/litellm/blob/litellm_internal_staging/docker-compose.yml
- Docker README: https://github.com/berriai/litellm/blob/litellm_internal_staging/docker/README.md
- Contributing guide (Docker build): https://github.com/berriai/litellm/blob/litellm_internal_staging/CONTRIBUTING.md
- Proxy config reference: https://github.com/berriai/litellm/blob/litellm_internal_staging/cookbook/logging_observability/LiteLLM_Proxy_Langfuse.ipynb
- Ollama integration: https://github.com/berriai/litellm/blob/litellm_internal_staging/cookbook/liteLLM_Ollama.ipynb
- Health check client: https://github.com/berriai/litellm/blob/litellm_internal_staging/scripts/health_check/health_check_client_README.md
- .env.example: https://github.com/berriai/litellm/blob/litellm_internal_staging/.env.example
