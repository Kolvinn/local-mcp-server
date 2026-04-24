# Task Plan: Agentic Team Architecture for OpenCode

## Goal
Design and implement a multi-agent team structure for the local-mcp-server project, enabling specialized agents with proper delegation, lifecycle control, and domain expertise — moving from a single generic `coder` to a 5-agent team (explorer, expert, implementer, reviewer) with 3-layer delegation (why/how/what) and user approval gates at every stage.

## Current Phase
Phase 2

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

### Phase 2: Agent Team Architecture — Revised for 5-Agent Model
- [x] Redesign team: Coordinator (why), Expert (how), Explorer (scout), Implementer (what), Reviewer (verify)
- [x] Define expert agent: `all`-mode, baked-in **domain knowledge only** (FastMCP, Mem0, architecture patterns, Python/MCP best practices). NOT project ADRs or key facts — coordinator passes those per-task.
- [x] Define implementer agent: `subagent`-mode, lean prompt with Python/FastMCP syntax only
- [x] Define user approval gates: expert options → user approval → implementer spec → user approval → review → user sign-off
- [x] Draft expert prompt: domain principles + skill index (lazy loading) + anti-staleness rules
- [x] Draft implementer prompt: syntax-focused, spec-driven, project conventions baked in
- [x] Draft reviewer prompt: priority-based review framework (Blocker/Major/Minor/Suggestion), spec compliance checklist
- [x] Update coordinator prompt: 3-layer delegation, user gates, agent table, @expert delegation instead of @technical_expert
- [x] Update opencode.jsonc: add expert (all), rename coder→implementer (subagent), add reviewer (subagent), update coordinator task permissions
- [ ] Map delegation flows: what project context coordinator passes to expert per task (ADRs, key facts, goal scope)
- [ ] Test delegation flow: coordinator → expert → user → implementer → user → reviewer → user
- **Status:** mostly complete — delegation flow mapping remains

### Phase 3: Configuration Changes (opencode.jsonc + prompts)
- [x] Add `expert` agent to opencode.jsonc (mode: `all`, model: kimi-k2.5, prompt: `{file:./prompts/expert.md}`)
- [x] Rename `coder` → `implementer` in opencode.jsonc with lean syntax-focused prompt
- [x] Create `prompts/expert.md` — domain principles + skill index + anti-staleness rules. Project context passed per-task by coordinator.
- [x] Create `prompts/implementer.md` — Python/FastMCP syntax + spec-driven implementation instruction
- [x] Create `prompts/reviewer.md` — priority-based review framework, spec compliance checklist, read-only
- [x] Update coordinator prompt: 3-layer delegation, user gates, @expert delegation, project context passing
- [x] Update coordinator permissions: `task: { "expert": "allow", "implementer": "allow", "explorer": "allow", "reviewer": "allow" }`
- **Status:** complete

### Phase 4: Plugin Integration — Background Delegation
- [ ] Install `opencode-background-agents` plugin via opencode.jsonc `plugin` array
- [ ] Test `delegate(prompt, agent)` tool for read-only agent delegation (explorer, reviewer)
- [ ] Test `delegation_read(id)` and `delegation_list()` tools
- [ ] Verify results persist across session compaction
- [ ] Document working patterns in findings
- **Status:** pending

### Phase 5: Custom Plugin — Write-Capable Delegation (if needed)
- [ ] Create `.opencode/plugins/delegate-write.ts` using @opencode-ai/sdk
- [ ] Implement `delegate_write(prompt, agent)` tool that spawns sessions with write permissions
- [ ] Implement `delegate_write_result(id)` tool to read results
- [ ] Test with implementer agent (needs edit/bash write access)
- [ ] Verify lifecycle: create session → prompt → monitor → read result → cleanup
- **Status:** pending

### Phase 6: Workflow Automation Evaluation
- [ ] Evaluate `@openspoon/subtask2` for prompt chaining between agents
- [ ] Evaluate `opencode-conductor` for formalized workflow (Context → Spec → Plan → Implement)
- [ ] Evaluate `opencode-workspace` for bundled multi-agent orchestration
- [ ] Decide: adopt any of these, or keep custom coordination?
- [ ] If adopting, install and integrate into coordinator workflow
- **Status:** pending

### Phase 7: Verification & Documentation
- [ ] Test full delegation flow: coordinator → user gate → expert → user gate → implementer → user gate → reviewer → user sign-off
- [ ] Verify expert has full domain knowledge (ask about FastMCP patterns, Mem0 integration, ADRs)
- [ ] Verify implementer receives and implements specs correctly
- [ ] Test parallel delegation (explorer + reviewer running concurrently)
- [ ] Update `docs/project_notes/key_facts.md` with agent team reference
- [ ] Update `docs/project_notes/decisions.md` with ADRs for agent team architecture
- [ ] Update `docs/project_notes/issues.md` with implementation status
- **Status:** pending

## Key Questions
1. ~~Should reviewer have write access?~~ → Start read-only, escalate if workflow friction
2. ~~Should we use Server API or Task tool for delegation?~~ → Task tool for now (immediate), Server API via plugin later
3. ~~Do we need a custom plugin for write delegation?~~ → Only if background-agents proves insufficient for implementer
4. Should expert use `opencode-go/kimi-k2.5` or a different model? (current: kimi-k2.5 — good reasoning + context window)
5. Should we evaluate `opencode-skillful` for dynamic skill loading in expert agent? (baking into prompt works for v1, skillful could help with prompt size)
6. How do skills get injected into plugin-spawned sessions? (needs testing)
7. Stretch goal: Expert directly injects context into implementer — how? (v2 investigation)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 5 agents: coordinator, expert, explorer, implementer, reviewer | 3-layer model: why/how/what + verify (ADR-017, ADR-018) |
| Expert is `all`-mode | User can Tab-switch to expert for direct questions; also delegatable by coordinator |
| Expert owns domain knowledge (baked into prompt) | Eliminates coordinator as middleman; ADR-017 supersedes ADR-016 |
| Coordinator owns project context (passed per-task) | Expert only knows current goal scope; no stale project context in prompt |
| Implementer is lean (syntax only) | Receives approved specs from coordinator; no domain architecture in prompt |
| User approval gates at every stage | No autonomous pipeline; user signs off on expert options, implementation, and verification |
| Task tool as primary delegation (Phase 3) | Zero config overhead, works immediately |
| background-agents for async read-only delegation | Adds delegate/delegation_read/delegation_list tools, persists across compaction |
| Reviewer starts read-only | Verification should not modify; escalate if workflow friction |
| Tiered delegation: Task → CLI → Server API | Right mechanism for right complexity level |
| Skills baked into expert prompt for v1 | Reliable, always available; opencode-skillful evaluation deferred to v2 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| npx not available | 1 | Use bunx instead (project constraint: no Node.js) |
| GitHub repo 404s for some ecosystem plugins | 1 | Use npm registry API for package metadata instead |
| Explorer agent can't webfetch | 1 | Webfetch from coordinator directly; explorer is read-only codebase scout |

## Notes
- Existing task_plan.md / findings.md / progress.md are for the MCP server architecture (complete, Phase 5/5)
- This plan (task_plan_agents.md) is a separate planning track for the agent team
- ADR-015 and ADR-016 superseded by ADR-017 and ADR-018
- Phase 1 was 3-agent design; Phase 2 redesigns to 5-agent model with user gates
- Skills installation (subagent-creator, fastmcp, code-review-quality) will happen outside this session
- The `opencode-background-agents` plugin uses @opencode-ai/sdk — same SDK as custom plugin would use
- Plugin load order: global config → project config → global plugins dir → project plugins dir
- Markdown agent files can also define agents: `.opencode/agents/*.md` or `~/.config/opencode/agents/*.md`
