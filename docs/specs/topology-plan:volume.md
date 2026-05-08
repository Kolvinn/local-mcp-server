
## 2. Volume Topology

### 2.1 Named Volumes

| Volume | Type | Purpose | Creates It |
|--------|------|---------|------------|
| `project-vol` | Named, external | Source of truth for all project files (src/, docs/, .opencode/, etc.) | Created by user outside docker-compose |
| `agent-orchestrator-vol` | Auto-created | Orchestrator's workspace for task configs and state | docker-compose |
| `agent-strategic_thinker-vol` | Auto-created | Workspace for strategic_thinker variation | docker-compose |
| `agent-rag_thinker-vol` | Auto-created | Workspace for rag_thinker variation | docker-compose |
| `agent-architect_thinker-vol` | Auto-created | Workspace for architect_thinker variation | docker-compose |
| `agent-python_implementer-vol` | Auto-created | Workspace for python_implementer variation | docker-compose |
| `agent-infra_implementer-vol` | Auto-created | Workspace for infra_implementer variation | docker-compose |
| `agent-code_auditor-vol` | Auto-created | Workspace for code_auditor variation | docker-compose |
| `agent-codebase_explorer-vol` | Auto-created | Workspace for codebase_explorer variation | docker-compose |
| `agent-dependency_explorer-vol` | Auto-created | Workspace for dependency_explorer variation | docker-compose |

### 2.2 Mount Matrix

| Container | Mounts `project-vol` | Mounts Own `agent-*-vol` | Mounts Other Agent Volumes |
|-----------|---------------------|--------------------------|---------------------------|
| **Orchestrator** | rw | rw (its own workspace) | rw (ALL agent volumes — for symlink bridge) |
| **Agent (any variation)** | No | rw (only its own) | No (filesystem isolation) |

### 2.3 Symlink Bridge Mechanics

The orchestrator dynamically creates symlinks from `project-vol` into agent volumes:

```bash
# Grant access: agent will see /workspace/src/ as symlinks to project-vol
ln -s /project-vol/src /agent-vols/python_implementer/workspace/src
ln -s /project-vol/docs/specs/foo.md /agent-vols/python_implementer/workspace/foo.md

# Revoke access (after task completion)
rm /agent-vols/python_implementer/workspace/src
rm /agent-vols/python_implementer/workspace/foo.md
```

**Key properties:**
- Agent writes follow symlinks → land in `project-vol` (source of truth)
- Agent creates new files at symlink target → appear in `project-vol` automatically
- Zero copies — symlink is a pointer, not a copy
- Zero host access — agents never touch the host filesystem
- Dynamic grants — orchestrator adds/removes symlinks without container restarts
- Agent only sees what the orchestrator grants — filesystem isolation per task

### 2.4 Volume Paths Inside Containers

| Volume | Mount Path in Orchestrator | Mount Path in Agent |
|--------|---------------------------|---------------------|
| `project-vol` | `/project-vol` | N/A (agent never mounts it) |
| `agent-orchestrator-vol` | `/workspace` | N/A |
| `agent-{variation}-vol` | `/agent-vols/{variation}` | `/workspace` |

**Critical invariant:** The orchestrator sees agent volumes at `/agent-vols/{variation}/`, but the agent sees its own volume at `/workspace/`. The orchestrator creates symlinks at `/agent-vols/{variation}/workspace/` → `/project-vol/...`. The agent container, seeing `/workspace/`, follows the symlinks transparently.

