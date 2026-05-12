"""Bootstrap system validation and manifest generation."""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from typing import Any

from agent_framework.schema import AgentConfig, Manifest, ProjectConfig

# ---------------------------------------------------------------------------
# Registered types (from spec §4)
# ---------------------------------------------------------------------------
REGISTERED_TYPES: set[str] = {
    "orchestrator",
    "system_thinker",
    "implementer",
    "auditor",
    "explorer",
    "memory_manager",
}

# ---------------------------------------------------------------------------
# Defaults loading
# ---------------------------------------------------------------------------

_DEFAULTS_PATH: Path = Path(__file__).with_name("defaults.json")


def load_defaults() -> dict[str, Any]:
    """Load the built-in agent type defaults.

    Returns:
        Dict mapping agent type to its default configuration.
    """
    return json.loads(_DEFAULTS_PATH.read_text())["agent_types"]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
AGENT_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
MODEL_RE = re.compile(r"^[a-z0-9_-]+:[a-zA-Z0-9_.-]+$")


def validate_project_name(name: str) -> str | None:
    """Validate a project name.

    Returns:
        Error message if invalid, None if ok.
    """
    if not PROJECT_NAME_RE.match(name):
        return (
            "project_name must be lowercase alphanumeric with hyphens/underscores, "
            "1-63 chars"
        )
    return None


def validate_agent_key(key: str) -> str | None:
    """Validate an agent key.

    Returns:
        Error message if invalid, None if ok.
    """
    if not AGENT_KEY_RE.match(key):
        return (
            f"agent key '{key}' must be lowercase alphanumeric with underscores, 1-30 chars"
        )
    if "-" in key:
        return f"agent key '{key}' must not contain hyphens (use underscores)"
    return None


def validate_type(agent_type: str) -> str | None:
    """Validate an agent type against the registered type registry.

    Returns:
        Error message if invalid, None if ok.
    """
    if agent_type not in REGISTERED_TYPES:
        return (
            f"agent type '{agent_type}' is not registered. "
            f"Known types: {sorted(REGISTERED_TYPES)}"
        )
    return None


def validate_skills(
    skills: list[str],
    project_skills_dir: Path | None,
) -> str | None:
    """Validate that every listed skill has a SKILL.md file.

    Args:
        skills: List of skill names from the agent config.
        project_skills_dir: Path to shared/skills/ directory. If None,
            skill existence is not validated (useful when running outside
            a fully bootstrapped project).

    Returns:
        Error message if invalid, None if ok.
    """
    if project_skills_dir is None:
        return None
    for skill in skills:
        skill_path = project_skills_dir / skill / "SKILL.md"
        if not skill_path.exists():
            return f"skill '{skill}' not found at {skill_path}"
        content = skill_path.read_text()
        if "---" not in content:
            return f"skill '{skill}' SKILL.md missing YAML frontmatter"
    return None


def validate_graph_module(graph_module: str | None) -> str | None:
    """Validate that a graph module is importable and exposes get_graph().

    .. note::
        This requires the graph module to be importable in the **host**
        Python environment where bootstrap runs. Ensure the agent framework
        repo (or relevant packages) are installed in the host environment.

    Args:
        graph_module: Python dotted module path, or None.

    Returns:
        Error message if invalid, None if ok (or None input).
    """
    if graph_module is None:
        return None
    try:
        mod = importlib.import_module(graph_module)
    except ImportError as exc:
        return f"graph_module '{graph_module}' cannot be imported: {exc}"
    except Exception as exc:
        return f"graph_module '{graph_module}' validation failed: {exc}"

    if not hasattr(mod, "get_graph"):
        return f"graph_module '{graph_module}' must expose get_graph()"

    try:
        graph = mod.get_graph()
    except Exception as exc:
        return f"graph_module '{graph_module}' get_graph() failed: {exc}"

    # Deferred: strict CompiledStateGraph isinstance check requires
    # langgraph in host environment. We do a duck-type check to avoid
    # hard-depending on langgraph at bootstrap time.
    if not hasattr(graph, "invoke"):
        return (
            f"graph_module '{graph_module}' get_graph() must return a "
            "CompiledStateGraph (missing 'invoke' method)"
        )
    return None


# ---------------------------------------------------------------------------
# Config processing
# ---------------------------------------------------------------------------


def apply_defaults(agent: AgentConfig, agent_type: str, defaults: dict[str, Any]) -> AgentConfig:
    """Return a new AgentConfig with type defaults filled in for omitted fields.

    Args:
        agent: Raw agent config from YAML.
        agent_type: Resolved agent type string.
        defaults: Dict loaded from defaults.json.

    Returns:
        New AgentConfig with defaults applied.
    """
    type_defaults = defaults.get(agent_type, {})
    data = agent.model_dump()

    if data.get("graph_module") is None and type_defaults.get("graph_module"):
        data["graph_module"] = type_defaults["graph_module"]

    if data.get("system_prompt") is None and data.get("system_prompt_file") is None:
        if type_defaults.get("system_prompt_file"):
            data["system_prompt_file"] = type_defaults["system_prompt_file"]

    if not data.get("skills") and type_defaults.get("skills"):
        data["skills"] = list(type_defaults["skills"])

    return AgentConfig.model_validate(data)


def generate_manifest(
    agent_key: str,
    agent: AgentConfig,
    project_name: str,
) -> Manifest:
    """Generate a manifest for a single agent.

    Args:
        agent_key: The agent's key (also its volume subpath).
        agent: Fully-resolved AgentConfig.
        project_name: Project name for volume naming.

    Returns:
        Manifest ready to be serialized to JSON.
    """
    system_prompt: str | None = agent.system_prompt

    if system_prompt is None and agent.system_prompt_file:
        # Read prompt file relative to project root.
        # NOTE: This assumes bootstrap runs inside the project repo.
        prompt_path = Path(agent.system_prompt_file)
        if prompt_path.exists():
            system_prompt = prompt_path.read_text()

    return Manifest(
        agent_key=agent_key,
        agent_type=agent.type,
        model=agent.model,
        system_prompt=system_prompt,
        graph_module=agent.graph_module,
        skills=agent.skills,
        mcp_endpoints=[ep.model_dump(exclude_none=True) for ep in agent.mcp_endpoints],
        interrupt_on=agent.interrupt_on,
        permissions=[p.model_dump() for p in agent.permissions],
    )


# ---------------------------------------------------------------------------
# Top-level validation
# ---------------------------------------------------------------------------


def validate_config(
    config: ProjectConfig,
    project_skills_dir: Path | None = None,
    validate_graphs: bool = True,
) -> list[str]:
    """Validate a ProjectConfig and return a list of error messages.

    Args:
        config: Parsed project configuration.
        project_skills_dir: Path to shared/skills/ for skill validation.
            If None, skill existence is skipped.
        validate_graphs: Whether to attempt importing graph modules.
            Disabled when running outside the agent framework host env.

    Returns:
        List of error strings (empty if valid).
    """
    errors: list[str] = []

    if err := validate_project_name(config.project_name):
        errors.append(err)

    for key, agent in config.agents.items():
        if err := validate_agent_key(key):
            errors.append(err)
        if err := validate_type(agent.type):
            errors.append(err)
        if err := validate_skills(agent.skills, project_skills_dir):
            errors.append(err)
        if validate_graphs and (err := validate_graph_module(agent.graph_module)):
            errors.append(err)

    return errors
