## Exploration: Deep Agents Orchestration (from Context7 docs)

### Summary

Deep Agents provides three orchestration layers — **SubAgentMiddleware** (task delegation to specialized child agents), **TodoListMiddleware** (planning/tracking), and **HumanInTheLoopMiddleware** (interrupt-driven approval). All three are bundled automatically in `create_deep_agent()`. The CLI offers rich integration points (stdin pipe, `--skill`, streaming, ACP server), and streaming supports per-subagent namespace tracing for real-time TUI display.

### Relevance for LangChain/LangGraph → CLI TUI integration

If you are connecting a Deep Agent to a terminal UI:

- **Streaming is the key TUI enabler.** Use `agent.stream()` with `stream_mode="messages"` and `subgraphs=True` to get per-token output with namespace metadata (`chunk["ns"]`), letting a TUI render main-agent text vs. subagent tool calls in separate panels.
- **HITL interrupts map cleanly to TUI modal workflows.** The `interrupt()` primitive pauses execution and returns structured data (`result.interrupts[0].value`). A TUI can present this as a modal (approve/reject/edit), then resume via `Command(resume=...)`. Batched decisions (multiple tools needing approval) are supported as a decisions array.
- **The CLI itself is a reference TUI pattern.** The built-in CLI (`deepagents dev`, `deepagents --skill`, stdin piping, `-q` quiet mode) and the ACP server (`deepagents-acp`) show how to wrap agent invoke/stream loops. The `deepagents.toml` config file can drive theme/identity for a TUI.

---

### Key Findings

#### 1. SubAgentMiddleware — Multi-Agent Coordination

- **Config**: Defined as a list of dicts with `name`, `description`, `system_prompt`, `tools` passed to `create_deep_agent(subagents=[...])`.
- **Delegation**: Main agent uses a `task(agent="name", instruction="...")` tool. Subagents are **stateless** — complete instructions in a single call.
- **Context isolation**: Subagents keep the main agent's context clean. Results are compressed into a single report.
- **Custom subagents do NOT inherit** skills/tools from the main agent (must be explicit). The default "general-purpose" subagent does inherit.
- **Compiled subagents**: Can wrap existing LangGraph agents via `CompiledSubAgent(name=..., runnable=...)`.
- **HITL on subagents**: `interrupt_on={"tool_name": True}` can be set per-subagent to require approval on specific tools.

#### 2. CLI Connection to Running Agents

- **Commands**: `deepagents init`, `deepagents dev` (local dev server), `deepagents deploy` (production).
- **Config**: `deepagents.toml` with `[agent]` section (name, model) and optional theme.
- **Non-interactive mode**: Auto-detected when stdin is piped. Example: `echo "Explain this" | deepagents`.
- **Skill at launch**: `deepagents --skill code-review -n 'review patch' -q` (`-q` = quiet mode, agent output only on stdout).
- **Auto-approve**: `deepagents -y` or `--auto-approve` bypasses CLI approval prompts. `--shell-allow-list` for non-interactive shell commands.
- **ACP (Agent Communication Protocol)**: `deepagents-acp` package. Run `AgentServerACP(agent)` via stdio to expose any agent programmatically — a minimal server pattern.

#### 3. TUI/CLI Integration Patterns

- **Streaming API**: `agent.stream(..., stream_mode="messages", subgraphs=True, version="v2")` yields chunks with:
  - `chunk["type"]`: `"messages"`, `"updates"`, `"custom"`
  - `chunk["ns"]`: namespace — e.g., `["tools:subagent_name"]` for subagent events, empty for main agent
  - Tool call chunks stream incrementally (`token.tool_call_chunks`)
- **Differentiated rendering**: Check `any(s.startswith("tools:") for s in chunk["ns"])` to route main vs. subagent output to different TUI panels.
- **Three stream modes** can be combined: `["updates", "messages", "custom"]` for node-level progress, token streaming, and custom events.

#### 4. HITL Interrupt Patterns

- **Core primitive**: `interrupt(data_dict)` inside a tool — pauses graph execution.
- **Resume**: `agent.invoke(Command(resume={"approved": True}), config=config, version="v2")`.
- **Interrupt check**: `result.interrupts[0].value` (with `version="v2"`) returns the dict passed to `interrupt()`.
- **Configuration via `interrupt_on`**:
  - `True` → default (decisions: approve, edit, reject)
  - `False` → no interrupt
  - `{"allowed_decisions": ["approve", "reject"]}` → custom decisions
- **Batched interrupts**: Multiple tool calls requiring approval are batched into one interrupt with `action_requests` array. Decisions must be provided in the same order.
- **Edit pattern**: `Command(resume={"decisions": [{"type": "edit", "edited_action": {"name": "...", "args": {...}}}]})`.
- **Reject with feedback**: `Command(resume={"decisions": [{"type": "reject", "message": "..."}]})` — agent retries with a different approach.
- **Requirements**: `MemorySaver()` checkpointer + `thread_id` in config are mandatory for HITL. The checkpointer persists state across `invoke()` calls for resumption.

### Sources (Context7)

- `/websites/langchain_oss_python_deepagents` — SubAgentMiddleware, CLI, HITL, streaming, ACP
- `/langchain-ai/deepagents` — Quickstarts and deploy patterns
- `/websites/langchain_oss_python_langgraph` — Underlying LangGraph interrupt/checkpointer primitives
