"""Agent Controller CLI — user-facing commands inside the controller container."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

from agent_framework.controller.compose import ComposeGenerator
from agent_framework.controller.docker_ops import DockerOps
from agent_framework.controller.registry import AgentRecord, ProjectRegistry, Registry
from agent_framework.schema import load_config
from agent_framework.validators import generate_manifest, validate_config

app = typer.Typer(help="Agent Controller — manage containerised agent stacks")

DEFAULT_STATE_DIR = Path(os.environ.get("CONTROLLER_STATE_DIR", "/state"))
DEFAULT_COMPOSE_DIR = Path(os.environ.get("CONTROLLER_COMPOSE_DIR", "/state/compose"))


def _get_registry() -> Registry:
    return Registry(DEFAULT_STATE_DIR)


def _get_docker() -> DockerOps:
    return DockerOps()


def _get_compose_gen() -> ComposeGenerator:
    image = os.environ.get("AGENT_BASE_IMAGE", "langgraph-agent-base:latest")
    return ComposeGenerator(agent_base_image=image)


# ------------------------------------------------------------------
# validate
# ------------------------------------------------------------------

@app.command()
def validate(
    config_path: Path = typer.Argument(..., help="Path to agent-project.yaml"),
    skills_dir: Path | None = typer.Option(
        None, help="Path to shared/skills/ for skill validation"
    ),
) -> None:
    """Validate an agent-project.yaml file."""
    try:
        config = load_config(config_path)
    except Exception as exc:
        typer.echo(f"Config load failed: {exc}", err=True)
        raise typer.Exit(code=1)

    errors = validate_config(config, project_skills_dir=skills_dir, validate_graphs=False)
    if errors:
        for err in errors:
            typer.echo(err, err=True)
        raise typer.Exit(code=1)

    typer.echo("Config is valid.")


# ------------------------------------------------------------------
# bootstrap
# ------------------------------------------------------------------

@app.command()
def bootstrap(
    config_path: Path = typer.Argument(..., help="Path to agent-project.yaml"),
    dry_run: bool = typer.Option(False, help="Print actions without executing"),
) -> None:
    """Bootstrap a full agent stack: volumes, manifests, compose, and start."""
    config = load_config(config_path)
    errors = validate_config(config, validate_graphs=False)
    if errors:
        for err in errors:
            typer.echo(err, err=True)
        raise typer.Exit(code=1)

    project = config.project_name
    project_vol = f"{project}_project_vol"
    agent_vol = f"{project}_agent_vol"
    flox_vol = f"{project}_flox_vol"
    compose_path = DEFAULT_COMPOSE_DIR / f"docker-compose.{project}.yml"

    docker = _get_docker()
    registry = _get_registry()
    compose_gen = _get_compose_gen()

    if dry_run:
        typer.echo(f"[dry-run] Would create volumes: {project_vol}, {agent_vol}, {flox_vol}")
        typer.echo(f"[dry-run] Would create subpaths: {list(config.agents.keys())}")
        typer.echo(f"[dry-run] Would seed {project_vol}")
        typer.echo(f"[dry-run] Would write manifests for {len(config.agents)} agents")
        typer.echo(f"[dry-run] Would generate compose: {compose_path}")
        typer.echo(f"[dry-run] Would run: docker compose -f {compose_path} up -d")
        return

    # 1. Volumes
    for vol_name in (project_vol, agent_vol, flox_vol):
        created = docker.ensure_volume(vol_name)
        typer.echo(f"Volume '{vol_name}' {'created' if created else 'already exists'}.")

    # 2. Subpaths
    docker.create_subpaths(agent_vol, list(config.agents.keys()))
    typer.echo(f"Subpaths created in {agent_vol}.")

    # 3. Seed project volume
    docker.seed_project_volume(project_vol, project)
    typer.echo(f"Project volume {project_vol} seeded.")

    # 4. Manifests
    for agent_key, agent in config.agents.items():
        manifest = generate_manifest(agent_key, agent, project)
        docker.write_manifest(agent_vol, agent_key, manifest.model_dump())
    typer.echo(f"Manifests written for {len(config.agents)} agents.")

    # 5. Compose
    DEFAULT_COMPOSE_DIR.mkdir(parents=True, exist_ok=True)
    compose_gen.generate(config, compose_path)
    typer.echo(f"Generated compose: {compose_path}")

    # 6. Start
    docker.compose_up(compose_path)
    typer.echo(f"Stack started for project '{project}'.")

    # 7. Registry
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
    typer.echo("Registry updated.")


# ------------------------------------------------------------------
# add-agent
# ------------------------------------------------------------------

@app.command()
def add_agent(
    config_path: Path = typer.Argument(..., help="Path to agent-project.yaml"),
    agent_key: str = typer.Argument(..., help="Agent key to add from config"),
) -> None:
    """Add a single agent to an existing project."""
    config = load_config(config_path)
    if agent_key not in config.agents:
        typer.echo(f"Agent '{agent_key}' not found in config.", err=True)
        raise typer.Exit(code=1)

    project = config.project_name
    agent = config.agents[agent_key]
    agent_vol = f"{project}_agent_vol"
    compose_path = DEFAULT_COMPOSE_DIR / f"docker-compose.{project}.yml"

    docker = _get_docker()
    registry = _get_registry()
    compose_gen = _get_compose_gen()

    # Ensure compose exists
    if not compose_path.exists():
        typer.echo(f"Compose file not found: {compose_path}", err=True)
        raise typer.Exit(code=1)

    # Create subpath
    docker.create_subpaths(agent_vol, [agent_key])

    # Write manifest
    manifest = generate_manifest(agent_key, agent, project)
    docker.write_manifest(agent_vol, agent_key, manifest.model_dump())

    # Update compose
    compose_gen.add_agent(compose_path, agent_key, agent, project)

    # Start service
    docker.compose_up(compose_path, service=agent_key)

    # Update registry
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
    proj_reg.compose_path = str(compose_path)
    proj_reg.last_updated = datetime.now(timezone.utc).isoformat()
    registry.set_project(proj_reg)

    typer.echo(f"Agent '{agent_key}' added to project '{project}'.")


# ------------------------------------------------------------------
# remove-agent
# ------------------------------------------------------------------

@app.command()
def remove_agent(
    project: str = typer.Argument(..., help="Project name"),
    agent_key: str = typer.Argument(..., help="Agent key to remove"),
) -> None:
    """Remove a single agent from a project."""
    compose_path = DEFAULT_COMPOSE_DIR / f"docker-compose.{project}.yml"
    docker = _get_docker()
    registry = _get_registry()

    if not compose_path.exists():
        typer.echo(f"Compose file not found: {compose_path}", err=True)
        raise typer.Exit(code=1)

    # Stop and remove container
    docker.compose_down(compose_path, service=agent_key)

    # Update compose file
    compose_gen = _get_compose_gen()
    compose_gen.remove_agent(compose_path, agent_key)

    # Update registry
    proj_reg = registry.get_project(project)
    if proj_reg and agent_key in proj_reg.agents:
        proj_reg.agents[agent_key].status = "destroyed"
        proj_reg.agents[agent_key].updated_at = datetime.now(timezone.utc).isoformat()
        proj_reg.last_updated = datetime.now(timezone.utc).isoformat()
        registry.set_project(proj_reg)

    typer.echo(f"Agent '{agent_key}' removed from project '{project}'.")


# ------------------------------------------------------------------
# list-agents
# ------------------------------------------------------------------

@app.command()
def list_agents(
    project: str = typer.Argument(..., help="Project name"),
) -> None:
    """List agents for a project."""
    registry = _get_registry()
    proj_reg = registry.get_project(project)
    if not proj_reg or not proj_reg.agents:
        typer.echo(f"No agents found for project '{project}'.")
        return

    typer.echo(f"Agents for project '{project}':")
    for key, rec in proj_reg.agents.items():
        typer.echo(f"  {key}: type={rec.agent_type}, model={rec.model}, status={rec.status}, endpoint={rec.endpoint}")


# ------------------------------------------------------------------
# teardown
# ------------------------------------------------------------------

@app.command()
def teardown(
    config_path: Path = typer.Argument(..., help="Path to agent-project.yaml"),
    force: bool = typer.Option(False, help="Skip confirmation prompt"),
) -> None:
    """Tear down a project: stop containers, remove volumes, delete compose."""
    config = load_config(config_path)
    project = config.project_name
    project_vol = f"{project}_project_vol"
    agent_vol = f"{project}_agent_vol"
    flox_vol = f"{project}_flox_vol"
    compose_path = DEFAULT_COMPOSE_DIR / f"docker-compose.{project}.yml"

    if not force:
        typer.echo(
            f"WARNING: This will remove volumes {project_vol}, {agent_vol}, {flox_vol} "
            f"and delete {compose_path}. Data will be lost."
        )
        confirm = typer.prompt("Proceed? [y/N]", default="n")
        if confirm.lower() != "y":
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    docker = _get_docker()
    registry = _get_registry()

    # Stop and remove all services
    if compose_path.exists():
        docker.compose_down(compose_path)
        compose_path.unlink()
        typer.echo(f"Removed compose file: {compose_path}")

    # Remove volumes
    for vol_name in (project_vol, agent_vol, flox_vol):
        removed = docker.remove_volume(vol_name, force=True)
        typer.echo(f"Volume '{vol_name}' {'removed' if removed else 'not found'}.")

    # Remove registry entry
    registry.delete_project(project)
    typer.echo(f"Project '{project}' torn down.")


# ------------------------------------------------------------------
# registry
# ------------------------------------------------------------------

@app.command()
def show_registry() -> None:
    """Show full controller registry."""
    registry = _get_registry()
    projects = registry.list_projects()
    if not projects:
        typer.echo("No projects in registry.")
        return

    for project_name in projects:
        proj_reg = registry.get_project(project_name)
        if not proj_reg:
            continue
        typer.echo(f"\nProject: {project_name}")
        typer.echo(f"  Compose: {proj_reg.compose_path or 'N/A'}")
        typer.echo(f"  Last updated: {proj_reg.last_updated or 'N/A'}")
        typer.echo(f"  Agents:")
        for key, rec in proj_reg.agents.items():
            typer.echo(
                f"    {key}: {rec.status} ({rec.agent_type}) @ {rec.endpoint or 'N/A'}"
            )


# ------------------------------------------------------------------
# entry point
# ------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()
