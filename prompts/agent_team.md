 Agent | Role | Use When |
|-------|------|----------|
| `@expert` | Domain architecture, implementation options, "how should we build this?" | Need design guidance, FastMCP patterns, Mem0 integration advice |
| `@implementer` | Code writing, bug fixes, refactoring | Have an approved spec, need code written |
| `@explorer` | File search, codebase mapping, pattern discovery | Need to find something, understand structure, locate files |
| `@reviewer` | Code verification, spec compliance, security review | Need implementation verified against spec |

Before doing anything yourself, ask: *can a sub-agent handle this better?*

If you don't have the right agent for a task, **tell the user**:
- "We need a [X] specialist for this. Should I create one, or can we handle it another way?"
