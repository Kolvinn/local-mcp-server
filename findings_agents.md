# Findings: Agentic Team Architecture

## Requirements
- Multi-agent team that can tackle 7 implementation priorities in docs/project_notes/issues.md
- Current `coder` agent is too generic — no specialization, no verification loop
- Must be able to spawn agents with lifecycle control via CLI or server
- Skills must feed into agent context appropriately
- Must work within OpenCode ecosystem constraints (no Node.js, use bun)

## Research Findings

### OpenCode Agent Configuration (agents.mdx)

**Agent types:**
- `primary` — Main assistants (Build, Plan), switchable via Tab
- `subagent` — Specialized helpers invoked via @ mention or Task tool
- `all` — Appears in both contexts

**Built-in agents:**
| Agent | Mode | Description |
|-------|------|-------------|
| `build` | primary | Default, all tools enabled |
| `plan` | primary | Restricted, edit/bash = "ask" |
| `general` | subagent | Full tool access except todo |
| `explore` | subagent | Fast, read-only |
| `compaction` | primary | Hidden, auto-compacts long context |
| `title` | primary | Hidden, generates session titles |
| `summary` | primary | Hidden, creates session summaries |

**Agent config options:**
```json
{
  "agent": {
    "name": {
      "description": "required",
      "mode": "primary|subagent|all",
      "model": "provider/model-id",
      "prompt": "{file:./prompts/name.md}",
      "temperature": 0.0-1.0,
      "steps": 10,
      "hidden": true,
      "disable": true,
      "color": "#FF5733",
      "top_p": 0.9,
      "permission": {
        "edit": "ask|allow|deny",
        "bash": "ask|allow|deny" | { "*": "ask", "git status *": "allow" },
        "webfetch": "ask|allow|deny",
        "task": { "*": "deny", "specific-agent": "allow" }
      }
    }
  }
}
```

**Markdown agent files:**
- Global: `~/.config/opencode/agents/*.md`
- Per-project: `.opencode/agents/*.md`

**Multi-agent navigation:**
- `session_child_first` — Enter first child session
- `session_child_cycle` / `session_child_cycle_reverse` — Navigate children
- `session_parent` — Return to parent

### CLI Agent Commands (cli.mdx)

```bash
opencode agent create           # Interactive agent creation
opencode agent list             # List all agents
opencode run --agent <name> "prompt"  # Run with specific agent
opencode serve --agent <name>   # Start server with default agent
```

### Server API for Agent Control (server.mdx)

**Session lifecycle:**
```
POST /session                     → Create session (body: { parentID?, title? })
POST /session/:id/message         → Send message (body: { agent?, model?, parts })
POST /session/:id/prompt_async   → Send message async (returns 204 immediately)
GET  /session/:id/children       → Get child sessions
POST /session/:id/abort          → Kill running session
DELETE /session/:id              → Delete session and data
GET  /event                      → SSE stream for real-time events
```

**Message body supports:**
- `agent` — Specify which agent to use for this message
- `model` — Override model for this message
- `parts` — Array of content parts
- `noReply` — Inject context without AI response

### SDK for Programmatic Control (sdk.mdx)

```javascript
import { createOpencode } from "@opencode-ai/sdk"
const { client } = await createOpencode()

// Create session, prompt specific agent
const session = await client.session.create({ body: { title: "impl" } })
const result = await client.session.prompt({
  path: { id: session.id },
  body: { agent: "implementer", parts: [{ type: "text", text: "..." }] }
})

// Structured output from agents
const result = await client.session.prompt({
  path: { id: session.id },
  body: {
    parts: [{ type: "text", text: "Review this code" }],
    format: { type: "json_schema", schema: { /* ... */ } }
  }
})
```

### Plugin Architecture (plugins.mdx)

**Plugin locations:**
- `.opencode/plugins/` — Project-level
- `~/.config/opencode/plugins/` — Global
- npm packages in `opencode.jsonc` `plugin` array

**Plugin structure:**
```typescript
import type { Plugin } from "@opencode-ai/plugin"
export const MyPlugin: Plugin = async ({ project, client, $, directory, worktree }) => {
  return {
    // Hook implementations
    "tool.execute.before": async (input, output) => { /* ... */ },
    "tool.execute.after": async (input, output) => { /* ... */ },
    event: async ({ event }) => { /* ... */ },
    tool: {
      mytool: tool({
        description: "Custom tool",
        args: { foo: tool.schema.string() },
        async execute(args, context) { return `Hello ${args.foo}` }
      })
    }
  }
}
```

**Available events:**
- Session: `session.created`, `session.idle`, `session.error`, `session.compacted`, `session.updated`, `session.deleted`
- Message: `message.updated`, `message.part.updated`, `message.part.removed`
- Tool: `tool.execute.before`, `tool.execute.after`
- Permission: `permission.asked`, `permission.replied`
- Shell: `shell.env`
- File: `file.edited`, `file.watcher.updated`

**Custom tools via plugin:**
```typescript
import { tool } from "@opencode-ai/plugin"
tool: {
  mytool: tool({
    description: "Custom tool description",
    args: { input: tool.schema.string() },
    async execute(args, context) { return "result" }
  })
}
```

### Ecosystem Plugins — Key Findings

**opencode-background-agents (v0.1.1):**
- Adds `delegate(prompt, agent)`, `delegation_read(id)`, `delegation_list()` tools
- Async delegation — main conversation keeps going while subagent runs
- Results persisted to `~/.local/share/opencode/delegations/<project-id>/`
- **CRITICAL LIMITATION**: Background runs are always **read-only**, even for write-capable agents
- Notifications report status; wake-up event when all delegations complete
- Default timeout: 1 hour
- Uses `@opencode-ai/sdk` and `@opencode-ai/plugin`

**@openspoon/subtask2 (v0.3.9):**
- "Enhanced subtask control with return context and prompt chaining"
- Extends /commands into orchestration system with granular flow control
- Uses `@opencode-ai/sdk`

**opencode-conductor (v1.0.6):**
- Context-Driven Development workflow
- Implements Context → Spec → Plan → Implement lifecycle
- Commands: `/conductor-setup`, `/conductor-new`, `/conductor-do`, `/conductor-status`
- Grounds implementation in product.md, tech-stack.md, workflow.md
- Tracks feature "tracks" with spec.md + plan.md per track

**opencode-workspace:**
- "Bundled multi-agent orchestration harness — 16 components, one install"
- Could not access GitHub repo (404)

**opencode-skillful:**
- "Allow OpenCode agents to lazy load prompts on demand with skill discovery and injection"
- Potentially solves the skill injection problem for subagents

**opencode-dynamic-context-pruning:**
- "Optimize token usage by pruning obsolete tool outputs"
- Could help with context window management during long agent sessions

### Delegation Mechanisms Comparison

| Mechanism | Context | Tools | Execution | Lifecycle | Write Access |
|-----------|---------|-------|-----------|-----------|-------------|
| Task tool | Shared, limited | Subset via permissions | Sync, blocking | Auto-managed | Per-agent config |
| `opencode run` | Full, isolated | Full agent config | Sync via bash | Dies on completion | Per-agent config |
| Server API | Full, isolated | Full agent config | Async capable | Create→abort→delete | Per-agent config |
| background-agents | Full, isolated | **Read-only forced** | Async, persisted | Auto-managed | **No** |
| Custom plugin | Full, isolated | Full agent config | Async via SDK | Custom | Per-agent config |

### Skills Ecosystem — Key Findings

**subagent-creator (320 installs, 2.2K stars):**
- Patterns for creating agent prompts with frontmatter metadata
- Key patterns: verifier, debugger, security auditor, code reviewer
- Best practice: "Start with 2-3 focused subagents"
- Description determines when to delegate automatically
- Prompts should be concise but complete

**fastmcp (409 installs, 744 stars):**
- Comprehensive FastMCP v2.x and v3.0 patterns
- 30+ common errors with solutions
- Middleware, auth, storage, composition patterns
- Critical for implementer agent context

**code-review-quality (1.1K installs, 324 stars):**
- Priority-based feedback: Blocker → Major → Minor → Suggestion
- Four review areas: logic, security, testability, maintainability
- Agent-assisted reviews with parallel checks
- Review chunks < 400 lines for effectiveness

**opencode-expert (296 installs):**
- Comprehensive OpenCode reference guide
- CLI commands, agent configuration, skill discovery
- Useful as general reference for any opencode agent

### Tiered Delegation Architecture

```
┌─────────────────────────────────────────────────────┐
│                    COORDINATOR                       │
│                                                      │
│  Tier 1: Task tool (fast, in-process)                │
│  ├─ explorer: Quick searches, file finding           │
│  └─ Simple lookups that don't need isolated context   │
│                                                      │
│  Tier 2: CLI `opencode run` (full agent, blocking)   │
│  ├─ implementer: Write code, run tests               │
│  └─ reviewer: Code review, verification              │
│                                                      │
│  Tier 3: Server API / Plugin (full, async, lifecycle) │
│  ├─ Long-running implementation tasks                │
│  ├─ Parallel agent execution                        │
│  └─ Background research while coordinator continues  │
└─────────────────────────────────────────────────────┘
```

**Skill injection flow:**
```
1. Coordinator identifies what domain knowledge is needed
2. Coordinator delegates to expert, passing PROJECT CONTEXT (ADRs, key facts, goal scope)
3. Expert combines baked-in DOMAIN KNOWLEDGE with coordinator-provided project context
4. Expert returns condensed options to coordinator
5. Coordinator presents options to user for approval
6. Coordinator delegates approved spec to implementer
7. Reviewer verifies (read-only)
8. Coordinator presents final result to user for sign-off
```

NOTE: Expert prompt contains DOMAIN expertise only (FastMCP, Mem0, architecture patterns).
Project context (ADRs, key facts, current goal) is passed per-task by the coordinator.
This keeps expert prompt lean and prevents stale project context.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 3 agents: explorer, implementer, reviewer | Separation of write/verify prevents fox/henhouse problem |
| Task tool as primary delegation (Phase 2) | Zero config overhead, works immediately |
| Skills injected by coordinator into task prompts | Subagents can't load skills; coordinator enriches context |
| background-agents for async read-only delegation | Proper async, persists across compaction, correct for explorer/reviewer |
| Custom plugin for write delegation only if needed | Don't build what we don't need; test background-agents first |
| No separate architect agent | Architecture planning complete; need implementation + verification |
| reviewer starts read-only | Verification should not modify; escalate if workflow friction |

## Issues Encountered
| Issue | Resolution |
|-------|-----------|
| npx not available in environment | Use bunx (project constraint: no Node.js) |
| GitHub 404s for ecosystem plugins | Use npm registry API for package metadata |
| Explorer agent can't webfetch | Coordinator fetches web, passes context to explorer |
| background-agents read-only limitation | Implementer stays on Task tool; custom plugin if async needed |

## Resources
- OpenCode agents docs: https://opencode.ai/docs/agents/ (source: agents.mdx)
- OpenCode CLI docs: https://opencode.ai/docs/cli/ (source: cli.mdx)
- OpenCode server docs: https://opencode.ai/docs/server/ (source: server.mdx)
- OpenCode SDK docs: https://opencode.ai/docs/sdk/ (source: sdk.mdx)
- OpenCode plugins docs: https://opencode.ai/docs/plugins/ (source: plugins.mdx)
- OpenCode ecosystem: https://opencode.ai/docs/ecosystem/
- opencode-background-agents: npm `opencode-background-agents` v0.1.1
- @openspoon/subtask2: npm `@openspoon/subtask2` v0.3.9
- opencode-conductor: npm `opencode-conductor` v1.0.6
- GitHub docs source: anomalyco/opencode tree dev/packages/web/src/content/docs/
- Skills search: https://skills.sh/
- subagent-creator skill: https://skills.sh/tech-leads-club/agent-skills/subagent-creator
- fastmcp skill: https://skills.sh/jezweb/claude-skills/fastmcp
- code-review-quality skill: https://skills.sh/proffesor-for-testing/agentic-qe/code-review-quality

## Visual/Browser Findings
- N/A (all findings from text sources)

---
*Updated: 2026-04-23 — Session 004*
