"""Pydantic models for agent-project.yaml schema and generated manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MCPEndpoint(BaseModel):
    """MCP server endpoint configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,30}$")
    transport: Literal["http", "stdio"]
    url: str | None = Field(default=None)
    command: str | None = Field(default=None)
    args: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_transport_fields(self) -> MCPEndpoint:
        if self.transport == "http" and not self.url:
            raise ValueError(f"MCP endpoint '{self.name}': url is required when transport=http")
        if self.transport == "stdio" and not self.command:
            raise ValueError(
                f"MCP endpoint '{self.name}': command is required when transport=stdio"
            )
        return self


class Permission(BaseModel):
    """Filesystem permission rule."""

    model_config = ConfigDict(extra="forbid")

    path: str
    read: bool = Field(default=True)
    write: bool = Field(default=False)


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    model_config = ConfigDict(extra="forbid")

    type: str
    model: str = Field(pattern=r"^[a-z0-9_-]+:[a-zA-Z0-9_.-]+$")
    system_prompt: str | None = Field(default=None)
    system_prompt_file: str | None = Field(default=None)
    graph_module: str | None = Field(default=None)
    skills: list[str] = Field(default_factory=list)
    mcp_endpoints: list[MCPEndpoint] = Field(default_factory=list)
    interrupt_on: dict[str, bool | dict[str, Any]] = Field(default_factory=dict)
    permissions: list[Permission] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_prompt_exclusivity(self) -> AgentConfig:
        if self.system_prompt is not None and self.system_prompt_file is not None:
            raise ValueError(
                "system_prompt and system_prompt_file are mutually exclusive"
            )
        return self


class ProjectConfig(BaseModel):
    """Top-level agent-project.yaml configuration."""

    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    agents: dict[str, AgentConfig]


class Manifest(BaseModel):
    """Per-agent manifest written to agent_vol subpath."""

    model_config = ConfigDict(extra="forbid")

    agent_key: str
    agent_type: str
    model: str
    system_prompt: str | None = Field(default=None)
    graph_module: str | None = Field(default=None)
    skills: list[str] = Field(default_factory=list)
    mcp_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    interrupt_on: dict[str, bool | dict[str, Any]] = Field(default_factory=dict)
    permissions: list[dict[str, Any]] = Field(default_factory=list)
    workspace_path: str = "/workspace"
    project_path: str = "/app/project"
    skills_path: str = "/workspace/skills"


def load_config(path: Path) -> ProjectConfig:
    """Load and parse an agent-project.yaml file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Parsed ProjectConfig.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        ValueError: If the data does not match the schema.
    """
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("agent-project.yaml must be a YAML mapping")
    return ProjectConfig.model_validate(raw)
