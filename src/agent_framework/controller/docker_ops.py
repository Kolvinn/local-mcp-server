"""Docker operations for the controller — volumes, subpaths, compose execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import docker
from docker.errors import NotFound


class DockerOps:
    """Wrapper around docker-py for controller operations."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    # ------------------------------------------------------------------
    # Volumes
    # ------------------------------------------------------------------

    def ensure_volume(self, name: str) -> bool:
        """Create a volume if it doesn't exist. Returns True if created."""
        try:
            self._client.volumes.get(name)
            return False
        except NotFound:
            self._client.volumes.create(name=name, driver="local")
            return True

    def remove_volume(self, name: str, force: bool = False) -> bool:
        """Remove a volume. Returns True if removed."""
        try:
            vol = self._client.volumes.get(name)
            vol.remove(force=force)
            return True
        except NotFound:
            return False

    def volume_exists(self, name: str) -> bool:
        try:
            self._client.volumes.get(name)
            return True
        except NotFound:
            return False

    # ------------------------------------------------------------------
    # Subpath pre-creation
    # ------------------------------------------------------------------

    def create_subpaths(self, agent_vol: str, agent_keys: list[str]) -> None:
        """Create per-agent subdirectories inside agent_vol via alpine init container."""
        if not agent_keys:
            return
        cmds = []
        for key in agent_keys:
            cmds.append(f"mkdir -p /vol/{key}/skills")
            cmds.append(f"mkdir -p /vol/{key}/tools")
        cmds.append("echo 'Subdirectories created.'")
        command = " && ".join(cmds)
        self._client.containers.run(
            image="alpine:latest",
            command=["sh", "-c", command],
            volumes={agent_vol: {"bind": "/vol", "mode": "rw"}},
            remove=True,
        )

    def seed_project_volume(self, project_vol: str, project_name: str) -> None:
        """Create skeleton directories and README in project_vol."""
        command = (
            "mkdir -p /vol/shared/skills && "
            "mkdir -p /vol/shared/knowledge && "
            "mkdir -p /vol/shared/config && "
            f"echo '# Project: {project_name}' > /vol/README.md && "
            "echo 'Skeleton seeded.'"
        )
        self._client.containers.run(
            image="alpine:latest",
            command=["sh", "-c", command],
            volumes={project_vol: {"bind": "/vol", "mode": "rw"}},
            remove=True,
        )

    # ------------------------------------------------------------------
    # Manifest writing
    # ------------------------------------------------------------------

    def write_manifest(self, agent_vol: str, agent_key: str, manifest: dict[str, Any]) -> None:
        """Write manifest.json into an agent subpath via alpine init container."""
        manifest_json = json.dumps(manifest, indent=2)
        command = f"cat > /vol/{agent_key}/manifest.json << 'MANIFEST_EOF'\n{manifest_json}\nMANIFEST_EOF"
        self._client.containers.run(
            image="alpine:latest",
            command=["sh", "-c", command],
            volumes={agent_vol: {"bind": "/vol", "mode": "rw"}},
            remove=True,
        )

    # ------------------------------------------------------------------
    # Compose execution
    # ------------------------------------------------------------------

    def compose_up(self, compose_path: Path, service: str | None = None) -> None:
        """Run docker compose up for the given compose file."""
        cmd = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
        if service:
            cmd.append(service)
        subprocess.run(cmd, check=True)

    def compose_down(self, compose_path: Path, service: str | None = None) -> None:
        """Run docker compose down. If service is given, stops/removes only that service."""
        if service:
            # Stop and remove specific service without touching others
            subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "stop", service],
                check=False,
            )
            subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "rm", "-f", service],
                check=False,
            )
        else:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "down"],
                check=True,
            )

    def compose_config(self, compose_path: Path) -> dict[str, Any]:
        """Validate and return parsed compose config."""
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "config", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    # ------------------------------------------------------------------
    # Container inspection
    # ------------------------------------------------------------------

    def get_container_id(self, container_name: str) -> str | None:
        try:
            container = self._client.containers.get(container_name)
            return container.id
        except NotFound:
            return None
