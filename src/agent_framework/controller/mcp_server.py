"""MCP server exposing controller operations to the orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from agent_framework.controller.compose import ComposeGenerator
from agent_framework.controller.docker_ops import DockerOps
from agent_framework.controller.registry import AgentRecord, ProjectRegistry, Registry
from agent_framework.schema import load_config
from agent_framework.validators import generate_manifest, validate_config

mcp = FastMCP("agent-controller")

STATE_DIR = Path("/state")
COMPOSE_DIR = Path("/state/compose")


def _registry() -> Registry:
    return Registry(STATE_DIR)


def _docker() -> DockerOps:
    return DockerOps()


def _compose_gen() -> ComposeGenerator:
    import os
    image = os.environ.get("AGENT_BASE_IMAGE", "langgraph-agent-base:latest")
    return ComposeGenerator(agent_base_image=image)


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------

@mcp.tool()
def validate_project(config_path: str) -> dict[str, Any]:
    """Validate an agent-project.yaml file."""
    try:
        config = load_config(Path(config_path))
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)]}

    errors = validate_config(config, validate_graphs=False)
    return {"valid": not errors, "errors": errors}


@mcp.tool()
def bootstrap_project(config_path: str) -> dict[str, Any]:
    """Bootstrap a full agent stack from config."""
    config = load_config(Path(config_path))
    errors = validate_config(config, validate_graphs=False)
    if errors:
        return {"success": False, "errors": errors}

    project = config.project_name
    project_vol = f"{project}_project_vol"
    agent_vol = f"{project}_agent_vol"
    flox_vol = f"{project}_flox_vol"
    compose_path = COMPOSE_DIR / f"docker-compose.{project}.yml"

    docker = _docker()
    registry = _registry()
    compose_gen = _compose_gen()

    # Volumes
    for vol_name in (project_vol, agent_vol, flox_vol):
        docker.ensure_volume(vol_name)

    # Subpaths
    docker.create_subpaths(agent_vol, list(config.agents.keys()))

    # Seed
    docker.seed_project_volume(project_vol, project)

    # Manifests
    for agent_key, agent in config.agents.items():
        manifest = generate_manifest(agent_key, agent, project)
        docker.write_manifest(agent_vol, agent_key, manifest.model_dump())

    # Compose
    COMPOSE_DIR.mkdir(parents=True, exist_ok=True)
    compose_gen.generate(config, compose_path)

    # Start
    docker.compose_up(compose_path)

    # Registry
    proj_reg = ProjectRegistry(
        project_name=project,
        compose_path=str(compose_path),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )
    for agent_key, agent in config.agents.items():
        container_name = f"{project}_{agent_key}"
        container_id = docker.get_container_id(container_name)
        proj_reg.agents[agent_key] = AgentRecord(
            agent_key=agent_key,
            agent_type=agent.type,
            model=agent.model,
            status="running" if container_id else "error",
            endpoint=f"http://{container_name}:8000",
            container_id=container_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    registry.set_project(proj_reg)

    return {"success": True, "project": project, "agents": list(config.agents.keys())}


@mcp.tool()
def provision_agent(config_path: str, agent_key: str) -> dict[str, Any]:
    """Add a single agent to an existing project."""
    config = load_config(Path(config_path))
    if agent_key not in config.agents:
        return {"success": False, "error": f"Agent '{agent_key}' not found in config"}

    project = config.project_name
    agent = config.agents[agent_key]
    agent_vol = f"{project}_agent_vol"
    compose_path = COMPOSE_DIR / f"docker-compose.{project}.yml"

    if not compose_path.exists():
        return {"success": False, "error": f"Compose file not found: {compose_path}"}

    docker = _docker()
    registry = _registry()
    compose_gen = _compose_gen()

    docker.create_subpaths(agent_vol, [agent_key])
    manifest = generate_manifest(agent_key, agent, project)
    docker.write_manifest(agent_vol, agent_key, manifest.model_dump())
    compose_gen.add_agent(compose_path, agent_key, agent, project)
    docker.compose_up(compose_path, service=agent_key)

    proj_reg = registry.get_project(project) or ProjectRegistry(project_name=project)
    container_name = f"{project}_{agent_key}"
    container_id = docker.get_container_id(container_name)
    proj_reg.agents[agent_key] = AgentRecord(
        agent_key=agent_key,
        agent_type=agent.type,
        model=agent.model,
        status="running" if container_id else "provisioning",
        endpoint=f"http://{container_name}:8000",
        container_id=container_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    proj_reg.last_updated = datetime.now(timezone.utc).isoformat()
    registry.set_project(proj_reg)

    return {"success": True, "agent_key": agent_key, "endpoint": f"http://{container_name}:8000"}


@mcp.tool()
def destroy_agent(project: str, agent_key: str) -> dict[str, Any]:
    """Remove an agent from a project."""
    compose_path = COMPOSE_DIR / f"docker-compose.{project}.yml"
    docker = _docker()
    registry = _registry()

    if not compose_path.exists():
        return {"success": False, "error": f"Compose file not found: {compose_path}"}

    docker.compose_down(compose_path, service=agent_key)
    compose_gen = _compose_gen()
    compose_gen.remove_agent(compose_path, agent_key)

    proj_reg = registry.get_project(project)
    if proj_reg and agent_key in proj_reg.agents:
        proj_reg.agents[agent_key].status = "destroyed"
        proj_reg.agents[agent_key].updated_at = datetime.now(timezone.utc).isoformat()
        proj_reg.last_updated = datetime.now(timezone.utc).isoformat()
        registry.set_project(proj_reg)

    return {"success": True, "agent_key": agent_key}


@mcp.tool()
def list_agents(project: str) -> dict[str, Any]:
    """List all agents for a project."""
    registry = _registry()
    proj_reg = registry.get_project(project)
    if not proj_reg:
        return {"project": project, "agents": []}

    agents = []
    for key, rec in proj_reg.agents.items():
        agents.append({
            "agent_key": rec.agent_key,
            "agent_type": rec.agent_type,
            "model": rec.model,
            "status": rec.status,
            "endpoint": rec.endpoint,
        })
    return {"project": project, "agents": agents}


@mcp.tool()
def get_agent_endpoint(project: str, agent_key: str) -> dict[str, Any]:
    """Get the ACP endpoint for a specific agent."""
    registry = _registry()
    proj_reg = registry.get_project(project)
    if not proj_reg or agent_key not in proj_reg.agents:
        return {"found": False, "error": f"Agent '{agent_key}' not found in project '{project}'"}

    rec = proj_reg.agents[agent_key]
    return {
        "found": True,
        "agent_key": rec.agent_key,
        "endpoint": rec.endpoint,
        "status": rec.status,
    }


@mcp.tool()
def get_agent_status(project: str, agent_key: str) -> dict[str, Any]:
    """Check the runtime status of an agent."""
    registry = _registry()
    proj_reg = registry.get_project(project)
    if not proj_reg or agent_key not in proj_reg.agents:
        return {"found": False, "error": f"Agent '{agent_key}' not found in project '{project}'"}

    rec = proj_reg.agents[agent_key]
    docker = _docker()
    container_name = f"{project}_{agent_key}"
    container_id = docker.get_container_id(container_name)
    is_running = bool(container_id)
    return {
        "found": True,
        "agent_key": rec.agent_key,
        "status": "running" if is_running else rec.status,
        "container_id": container_id,
    }


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
