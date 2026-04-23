# Task Plan: Agentic Team Architecture for OpenCode

## Goal
Design and implement a multi-agent team structure for the local-mcp-server project, enabling specialized agents with proper delegation, lifecycle control, and skill injection — moving from a single generic `coder` to a structured team (explorer, implementer, reviewer) with tiered delegation mechanisms.

## Current Phase
Phase 1

## Phases

### Phase 1: Agent Team Structure Design
- [x] Research OpenCode agent configuration (agents.mdx, cli.mdx, server.mdx, sdk.mdx)
- [x] Research OpenCode plugin architecture (plugins.mdx, ecosystem page)
- [x] Research delegation mechanisms (Task tool, CLI run, Server API, plugins)
- [x] Research relevant ecosystem plugins (background-agents, subtask2, conductor, workspace)
- [x] Research relevant skills (subagent-creator, fastmcp, code-review-quality, opencode-expert)
- [x] Define 3-agent team structure (explorer, implementer, reviewer)
- [x] Define tiered delegation model (Task tool, CLI, Server API)
- [x] Define skill injection strategy (coordinator-side, per-delegation context enrichment)
- **Status:** complete

### Phase 2: Configuration Changes (opencode.jsonc + prompts)
- [ ] Rename `coder` → `implementer` in opencode.jsonc with refocused prompt
- [ ] Add `reviewer` agent to opencode.jsonc with read-only permissions + review prompt
- [ ] Update coordinator permissions: add `task: reviewer: allow`
- [ ] Update coordinator prompt: remove stale `@technical_expert`, add `@reviewer`
- [ ] Create `prompts/implementer.md` (was coder.md) with FastMCP/architecture context
- [ ] Create `prompts/reviewer.md` with code-review-quality patterns
- **Status:** pending

### Phase 3: Plugin Integration — Background Delegation
- [ ] Install `opencode-background-agents` plugin via opencode.jsonc `plugin` array
- [ ] Test `delegate(prompt, agent)` tool for read-only agent delegation
- [ ] Test `delegation_read(id)` and `delegation_list()` tools
- [ ] Verify results persist across session compaction
- [ ] Document working patterns in findings
- **Status:** pending

### Phase 4: Custom Plugin — Write-Capable Delegation (if needed)
- [ ] Create `.opencode/plugins/delegate-write.ts` using @opencode-ai/sdk
- [ ] Implement `delegate_write(prompt, agent)` tool that spawns sessions with write permissions
- [ ] Implement `delegate_write_result(id)` tool to read results
- [ ] Test with implementer agent (needs edit/bash write access)
- [ ] Verify lifecycle: create session → prompt → monitor → read result → cleanup
- **Status:** pending

### Phase 5: Workflow Automation Evaluation
- [ ] Evaluate `@openspoon/subtask2` for prompt chaining between agents
- [ ] Evaluate `opencode-conductor` for formalized workflow (Context → Spec → Plan → Implement)
- [ ] Evaluate `opencode-workspace` for bundled multi-agent orchestration
- [ ] Decide: adopt any of these, or keep custom coordination?
- [ ] If adopting, install and integrate into coordinator workflow
- **Status:** pending

### Phase 6: Verification & Documentation
- [ ] Test full delegation flow: coordinator → explorer → implementer → reviewer
- [ ] Verify skill injection works (coordinator loads skill, injects into task prompt)
- [ ] Test parallel delegation (explorer + reviewer running concurrently)
- [ ] Update `docs/project_notes/key_facts.md` with agent team reference
- [ ] Update `docs/project_notes/decisions.md` with ADR for agent team architecture
- [ ] Update `docs/project_notes/issues.md` with implementation status
- **Status:** pending

## Key Questions
1. ~~Should reviewer have write access?~~ → Start read-only, escalate if workflow friction
2. ~~Should we use Server API or Task tool for delegation?~~ → Task tool for now (immediate), Server API via plugin later
3. ~~Do we need a custom plugin for write delegation?~~ → Only if background-agents proves insufficient for implementer
4. Should implementer use `opencode-go/kimi-k2.5` or a different model? (current: kimi-k2.5)
5. Should reviewer share implementer's model or use a faster/cheaper one?
6. How do skills get injected into plugin-spawned sessions? (needs testing)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 3 agents: explorer, implementer, reviewer | Separation of write/verify, scout/build/check roles |
| Task tool as primary delegation (Phase 2) | Zero config overhead, works immediately |
| Skills are coordinator-side injection | Subagents can't load skills; coordinator enriches task prompts with skill knowledge |
| `opencode-background-agents` for async read-only delegation | Adds delegate/delegation_read/delegation_list tools, persists across compaction, read-only is correct for explorer/reviewer |
| Custom plugin only if needed (Phase 4) | background-agents may be sufficient; don't build what we don't need |
| No separate architect agent | Architecture planning is complete; implementation + verification is what we need now |
| Tiered delegation: Task → CLI → Server API | Right mechanism for right complexity level |
| Rename coder → implementer (not delete+create) | Preserves existing permissions structure, just refocuses prompt |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| npx not available | 1 | Use bunx instead (project constraint: no Node.js) |
| GitHub repo 404s for some ecosystem plugins | 1 | Use npm registry API for package metadata instead |
| Explorer agent can't webfetch | 1 | Webfetch from coordinator directly; explorer is read-only codebase scout |

## Notes
- Existing task_plan.md / findings.md / progress.md are for the MCP server architecture (complete, Phase 5/5)
- This plan (task_plan_agents.md) is a separate planning track for the agent team
- Skills installation (subagent-creator, fastmcp, code-review-quality) will happen outside this session
- The `opencode-background-agents` plugin uses @opencode-ai/sdk — same SDK as custom plugin would use
- Plugin load order: global config → project config → global plugins dir → project plugins dir
- Markdown agent files can also define agents: `.opencode/agents/*.md` or `~/.config/opencode/agents/*.md`
