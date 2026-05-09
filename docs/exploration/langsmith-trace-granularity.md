# LangSmith Trace Granularity — Research Findings

**Date:** 2026-05-09
**Source:** Context7 API queries to LangSmith documentation (`/websites/langchain_langsmith`)

---

## 1. What Data Does LangSmith Capture Per Individual Run/Trace?

Every run in LangSmith is a structured JSON object. Here are ALL fields captured automatically (based on the run schema):

### Core Identifiers
| Field | Type | Description |
|---|---|---|
| `id` | UUIDv7 string | Unique identifier for the run |
| `trace_id` | UUID string | Shared across all runs belonging to the same trace (top-level invocation) |
| `parent_run_id` | UUID or null | Points to the parent run for nested hierarchy; `null` for root runs |
| `dotted_order` | string | hierarchical ordering key (e.g., `20240919T171648Z<parent_uuid>.<child_uuid>`) — encodes the full ancestry |
| `session_id` | UUID | The tracing project/experiment this run belongs to |

### Timing
| Field | Type | Description |
|---|---|---|
| `start_time` | ISO 8601 datetime | When the run started |
| `end_time` | ISO 8601 datetime | When the run ended |
| `execution_order` | integer | (Deprecated) ordering number |

### Classification
| Field | Type | Description |
|---|---|---|
| `name` | string | Human-readable name (e.g., `"ChatOpenAI"`, `"agent"`, `"search_tool"`) |
| `run_type` | string | One of: `"llm"`, `"chain"`, `"tool"`, `"retriever"`, `"embedding"`, `"dataset"` |
| `status` | string | Run status (e.g., `"success"`, `"error"`) |

### Data Payloads
| Field | Type | Description |
|---|---|---|
| `inputs` | dict | Arbitrary JSON — the input to the run (prompt, messages, arguments) |
| `outputs` | dict | Arbitrary JSON — the output of the run (completion, tool result) |
| `error` | string or null | Error message if the run failed; `null` on success |
| `events` | array[dict] | Timeline events within the run (e.g., streaming events) |

### Metadata & Tagging
| Field | Type | Description |
|---|---|---|
| `tags` | array[string] | User-defined tags (e.g., `["production"]`, `["experiment-v2"]`) |
| `extra` / `metadata` | dict | Arbitrary key-value metadata. Common auto-set keys: `ls_provider`, `ls_model_name`, `ls_temperature`, `ls_run_depth` |

### Token Usage & Cost Tracking
| Field (via `usage_metadata` in extra/metadata or output) | Type | Description |
|---|---|---|
| `input_tokens` | integer | Prompt tokens |
| `output_tokens` | integer | Completion tokens |
| `total_tokens` | integer | Sum of input+output |
| `input_token_details.cache_read` | integer | Cached input tokens |
| `output_token_details` | dict | Per-output token breakdown |
| `input_cost` | float | Computed cost for input |
| `output_cost` | float | Computed cost for output |
| `total_cost` | float | Total cost |

### Feedback
| Field (associated via separate feedback object) | Type | Description |
|---|---|---|
| Feedback entries are linked by `run_id` — see Question 3 below |

---

## 2. Does LangSmith Capture Agent Decision Trees?

**Yes, completely.** LangSmith captures the full decision tree of an agent, including:

- **Which tool was called** (the child run's `name` field, e.g., `"search"`, `"listOrders"`)
- **What arguments were passed** (the child run's `inputs` — contains the tool's full input parameters)
- **What result was returned** (the child run's `outputs` — contains the tool's return value)
- **Which model made the decision** (the LLM child run's `metadata.ls_model_name`)
- **The LLM's reasoning** (the LLM child run's `outputs` — contains the message with `tool_calls`)

### Evidence from the docs:

The eval example `evaluate-graph` shows exactly this pattern:
```python
first_model_run = next(run for run in root_run.child_runs if run.name == "agent")
tool_calls = first_model_run.outputs["messages"][-1].tool_calls
right_tool = bool(tool_calls and tool_calls[0]["name"] == "search")
```

The export example `export-traces` shows grouping tool runs by their parent trace:
```python
tool_runs_by_parent[run.trace_id]["tools_involved"].add(run.name)
```

The RunTree API shows explicit parent → child relationships:
- Parent: `"My Chat Bot"` (run_type: `"chain"`)
  - Child: `"My Proprietary LLM"` (run_type: `"llm"`)
  - Child: `"transcript_loader"` (run_type: `"tool"`)

**Conclusion:** You can reconstruct the precise sequence of agent → LLM call → tool selection → tool arguments → tool result for every step.

---

## 3. Feedback/Annotation API

**Yes, LangSmith has a mature feedback/annotation API.**

### Endpoint
`POST https://api.smith.langchain.com/api/v1/feedback`

### Request body fields
| Field | Required | Description |
|---|---|---|
| `run_id` | Yes | The UUID of the run to annotate |
| `key` | Yes | Metric name (e.g., `"correctness"`, `"user-score"`, `"star_rating"`, `"ranked_preference"`) |
| `score` | No | Numeric score (float, e.g., 0.0–1.0 or 1–5) |
| `value` | No | Arbitrary value (alternative to or alongside score) |
| `comment` | No | Free-text comment |
| `correction` | No | Suggested correction data |
| `feedback_group_id` | No | Groups multiple feedback entries together (for comparative eval) |
| `comparative_experiment_id` | No | Links feedback to a comparative experiment |

### Feedback source tracking
Each feedback object tracks its origin:
```json
{
  "feedback_source": {
    "type": "app",          // or "api", "model"
    "metadata": null,
    "user_id": "ad52b092-..."
  }
}
```

### Usage patterns
- **Binary classification:** `score: 1.0` (good) / `score: 0.0` (bad)
- **Star rating:** `key: "star_rating", score: 4`
- **User thumbs up/down:** `key: "user-score", score: 1.0`
- **Comparative ranking:** Use `feedback_group_id` to rank outputs pairwise
- **Programmatic eval:** Eval functions can post feedback automatically after comparing outputs to expected values

### Python SDK shortcut
```python
client.create_feedback(
    run_id,
    key="user-score",
    score=1.0,
)
```

---

## 4. Querying/Filtering Runs

LangSmith provides powerful filtering via `client.list_runs()` (or `client.listRuns()` in TS) with a rich expression language.

### Filter operators available
| Operator | Meaning | Example |
|---|---|---|
| `eq(field, value)` | Equals | `eq(name, "ChatOpenAI")` |
| `neq(field, value)` | Not equals | `neq(error, null)` |
| `gt(field, value)` | Greater than | `gt(feedback_score, 4)` |
| `gte`, `lt`, `lte` | Comparison operators | `gte(metadata_value, 0.5)` |
| `has(tags, "value")` | Tag membership | `has(tags, "2aa1cf4")` |
| `and(...)` | Logical AND | `and(eq(name, "extractor"), eq(feedback_key, "user_score"))` |
| `or(...)` | Logical OR | (Available but not shown in snippets) |

### What you can filter by

| Dimension | Syntax | Example |
|---|---|---|
| **Run name** | `eq(name, "...")` | `eq(name, "extractor")` |
| **Run type** | `run_type` param | `run_type="llm"` |
| **Tags** | `has(tags, "...")` | `has(tags, "2aa1cf4")` |
| **Metadata key** | `eq(metadata_key, "...")` | `eq(metadata_key, "user_id")` |
| **Metadata value** | `eq(metadata_value, "...")` | `eq(metadata_value, "4070f233-...")` |
| **Metadata key+value** | `and(eq(metadata_key, ...), eq(metadata_value, ...))` | `and(eq(metadata_key, "environment"), eq(metadata_value, "production"))` |
| **Feedback key** | `eq(feedback_key, "...")` (in `trace_filter`) | `eq(feedback_key, "star_rating")` |
| **Feedback score** | `gt(feedback_score, N)` | `gt(feedback_score, 4)` |
| **Error presence** | `neq(error, null)` or `error=False` param | `neq(error, null)` |
| **Time range** | `start_time`/`end_time` params | `start_time=datetime.now() - timedelta(days=1)` |
| **Root vs child** | `is_root=True` param | Only root (top-level) runs |
| **Select fields** | `select=[...]` param | `select=["id", "outputs"]` |
| **Trace-level filter** | `trace_filter` param | Filter root runs whose *children* match feedback criteria |

### REST API alternative
```http
POST /api/v1/runs/query
{
  "session": ["experiment_id"],
  "is_root": true,
  "select": ["id", "reference_example_id", "outputs"],
  "filter": "eq(name, 'ChatOpenAI')"
}
```

---

## 5. Can LangSmith Serve as a "Decision Log" Without Custom Storage?

**Yes, for most practical purposes.** Here's the analysis:

### What LangSmith captures (good for decision logging):
- ✅ Full input/output for every step (agent decision, LLM call, tool call, retrieval)
- ✅ Hierarchical parent/child structure preserving the call graph
- ✅ Timing (start_time, end_time, latency)
- ✅ Error information per step
- ✅ Custom metadata (attach conversation_id, user_id, session_id, etc.)
- ✅ Feedback/annotations per run (human ratings, eval scores)
- ✅ Tag-based filtering for grouping runs
- ✅ Token usage and cost tracking
- ✅ Queryable via API with rich filters

### What LangSmith does NOT do (limitations):
- ❌ **No real-time streaming access** — data is available after runs complete (they are `post()`-ed and `patch()`-ed)
- ❌ **No transactional guarantees** — if your app crashes before `patch()` is called, the run may be incomplete
- ❌ **No local-only mode** — LangSmith is a cloud/SaaS service (self-hosted option available but limited)
- ❌ **No local-first/offline cache** — all data goes to LangSmith's servers
- ❌ **No built-in replay/state reconstruction** — you get the trace, but you'd need to replay logic separately
- ❌ **No causal dependency tracking** beyond parent/child (e.g., "tool B was called because tool A returned X" is inferred, not explicit)

### Verdict
**For most agent architectures (LangChain, LangGraph, custom with `@traceable`), LangSmith is sufficient as a decision log.** You can reconstruct:
- Which agent was invoked
- What the user's input was
- Which LLM was called and what it decided
- Which tool was selected, with what arguments
- What the tool returned
- Whether the agent looped or terminated
- What the final output was
- Whether errors occurred and where

**However**, if you need:
- Auditing-grade guarantees (immutable, append-only, signed logs)
- Low-latency decision lookup mid-conversation
- Running analytics queries across millions of decisions at interactive speed
- Fully air-gapped/local deployment

...then you should supplement with your own storage (e.g., a local SQLite/Postgres table with structured decision records).

---

## 6. Schema/Structure of LangChain/LangGraph Runs — Nested Runs

### Run Span Structure

Each run (span) has:
```
run {
  id: UUID
  trace_id: UUID          // same for all runs in one trace
  parent_run_id: UUID|null  // null = root
  dotted_order: string    // hierarchical: "timestampZ<parent_id>.timestampZ<child_id>.timestampZ<grandchild_id>"
  child_run_ids: [UUID]   // list of immediate children
  name: string
  run_type: "llm" | "chain" | "tool" | "retriever" | "embedding" | "dataset"
  inputs: dict
  outputs: dict
  error: string|null
  start_time: datetime
  end_time: datetime
  tags: [string]
  extra/metadata: dict
  events: [dict]
  status: string
}
```

### Nested Run Hierarchy (LangGraph Example)

A typical LangGraph trace looks like this when flattened:

```
Level 0 (root):    agent_graph           (run_type: "chain", parent_run_id: null)
├── Level 1:       agent_node            (run_type: "chain", parent_run_id: <root>)
│   ├── Level 2:   ChatOpenAI            (run_type: "llm",  parent_run_id: <agent_node>)
│   │   └── (outputs contain tool_calls array)
│   └── Level 2:   search_tool           (run_type: "tool", parent_run_id: <agent_node>)
│       └── (inputs contain tool args, outputs contain tool result)
├── Level 1:       agent_node (2nd call) (run_type: "chain", parent_run_id: <root>)
│   ├── Level 2:   ChatOpenAI            (run_type: "llm",  parent_run_id: <agent_node_2>)
│   └── Level 2:   final_answer_tool     (run_type: "tool", parent_run_id: <agent_node_2>)
└── Level 1:       final_output          (run_type: "chain", parent_run_id: <root>)
```

### How Hierarchy is Enforced

1. **`parent_run_id`** — each child points to its parent's `id`
2. **`trace_id`** — shared across ALL runs in the trace
3. **`dotted_order`** — a full-path ordering key:
   - Root: `20240919T171648Z<root_uuid>`
   - Child: `20240919T171648Z<root_uuid>.20240919T171648Z<child_uuid>`
   - Grandchild: `20240919T171648Z<root_uuid>.20240919T171648Z<child_uuid>.20240919T171648Z<grandchild_uuid>`
4. **`child_run_ids`** — parent lists its children (reverse lookup)

### Programmatic Access in Evaluators

The `Run` object exposes full child traversal:
```python
from langsmith.schemas import Run, Example

def evaluator(root_run: Run, example: Example) -> dict:
    # Navigate children by name
    agent_run = next(r for r in root_run.child_runs if r.name == "agent")
    # Access LLM outputs including tool_calls
    tool_calls = agent_run.outputs["messages"][-1].tool_calls
    # Access specific tool child
    tool_run = next(r for r in agent_run.child_runs if r.name == "search")
    tool_input = tool_run.inputs
    tool_output = tool_run.outputs
```

### RunTree API for Manual Control

LangSmith also provides the `RunTree` class for explicitly building trace hierarchies outside of LangChain/LangGraph:

```python
pipeline = RunTree(name="Chat Pipeline", run_type="chain", inputs={...})
child_llm = pipeline.create_child(name="OpenAI Call", run_type="llm", inputs={...})
child_tool = pipeline.create_child(name="search", run_type="tool", inputs={...})
# ... log data ...
child_llm.end(outputs=...)
child_tool.end(outputs=...)
pipeline.end(outputs=...)
pipeline.patch()
```

### LangGraph / LangChain Pass-Through

LangChain's `RunnableConfig` and LangGraph's state management automatically propagate the parent config to child runnables, so nesting is automatic and requires no manual wiring beyond passing `config`.

---

## Summary Table

| Question | Answer |
|---|---|
| 1. Fields captured | Full JSON: id, trace_id, parent_run_id, dotted_order, name, run_type, inputs, outputs, error, status, start_time, end_time, tags, metadata, events, usage_metadata (tokens), child_run_ids |
| 2. Agent decision trees | **Yes** — full tool_calls with arguments and results, traversable via `child_runs` |
| 3. Feedback/annotation API | **Yes** — `POST /api/v1/feedback` with run_id, key, score, comment, correction, feedback_source |
| 4. Query/filter capability | **Rich** — metadata, tags, feedback scores, error state, time range, run type, name, trace-level filters; `and`/`or`/`eq`/`neq`/`gt`/`has` operators |
| 5. Decision log adequacy | **Sufficient for most use cases** — full trace reconstruction possible; lacks only real-time, transactional, and air-gap guarantees |
| 6. Nested run preservation | **Yes** — 4-layer hierarchy (trace_id → parent_run_id → dotted_order → child_run_ids), arbitrary nesting depth |
