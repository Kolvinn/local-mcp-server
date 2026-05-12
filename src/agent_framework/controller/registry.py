"""Agent Controller — JSON registry for agent lifecycle state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentRecord:
    """Runtime record for a single agent."""

    agent_key: str
    agent_type: str
    model: str
    status: str  # "provisioning", "running", "stopped", "destroyed", "error"
    endpoint: str | None = None
    manifest_hash: str | None = None
    container_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    error_message: str | None = None


@dataclass
class ProjectRegistry:
    """Registry for a single project."""

    project_name: str
    agents: dict[str, AgentRecord] = field(default_factory=dict)
    compose_path: str | None = None
    last_updated: str | None = None


class Registry:
    """Persistent JSON registry for all projects managed by this controller."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = state_dir / "registry.json"
        self._data: dict[str, Any] = {"projects": {}}
        self._load()

    def _load(self) -> None:
        if self._registry_path.exists():
            self._data = json.loads(self._registry_path.read_text())
        else:
            self._data = {"projects": {}}
            self._save()

    def _save(self) -> None:
        self._registry_path.write_text(json.dumps(self._data, indent=2))

    def get_project(self, project_name: str) -> ProjectRegistry | None:
        raw = self._data["projects"].get(project_name)
        if raw is None:
            return None
        agents = {
            key: AgentRecord(**rec)
            for key, rec in raw.get("agents", {}).items()
        }
        return ProjectRegistry(
            project_name=project_name,
            agents=agents,
            compose_path=raw.get("compose_path"),
            last_updated=raw.get("last_updated"),
        )

    def set_project(self, project: ProjectRegistry) -> None:
        self._data["projects"][project.project_name] = {
            "agents": {
                key: asdict(rec)
                for key, rec in project.agents.items()
            },
            "compose_path": project.compose_path,
            "last_updated": project.last_updated,
        }
        self._save()

    def delete_project(self, project_name: str) -> bool:
        if project_name in self._data["projects"]:
            del self._data["projects"][project_name]
            self._save()
            return True
        return False

    def list_projects(self) -> list[str]:
        return list(self._data["projects"].keys())
