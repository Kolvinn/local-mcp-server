import os
import json
from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.exceptions import FastMCPError

# =====================================================================
# 1. GATEKEEPER CONFIGURATION
# =====================================================================
# A static representation of an RBAC (Role-Based Access Control) system.
# In production, this would query a database or an auth service.
AGENT_PERMISSIONS = {
    "agent_alpha": ["sequential_thinking", "memory_read"],
    "agent_admin": ["sequential_thinking", "memory_read", "memory_write"],
    "guest": []
}

# Map granular permissions to the actual underlying tool names
PERMISSION_TO_TOOLS = {
    "sequential_thinking": [
        "sequential_thinking__sequential_thinking"
    ],
    "memory_read": [
        "memory__search_memory",
        "memory__list_projects"
    ],
    "memory_write": [
        "memory__add_memory",
        "memory__delete_memory",
        "memory__sync_metadata"
    ]
}

# =====================================================================
# 2. ORCHESTRATOR INITIALIZATION
# =====================================================================
# We instantiate the main server. Agents will connect to this instance.
mcp = FastMCP("CompositeOrchestrator")

# =====================================================================
# 3. PROXY CONFIGURATION
# =====================================================================
# Define downstream services.
# - sequential_thinking runs as a local stdio subprocess.
# - memory_server runs as a separate HTTP/SSE service (as defined in mcp-memory.py).
proxy_config = {
    "mcpServers": {
        "sequential_thinking": {
            "command": "bunx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "headers": {"Accept": "application/json, text/event-stream"},
        },
        # "memory": {
        #     # Assuming mcp-memory.py is running independently on port 8000
        #     "url": "http://localhost:8000/sse",
        #     "headers": {"Accept": "application/json, text/event-stream"},
        # }
    }
}

# Mount the proxies. FastMCP automatically prefixes tools with the namespace.
# E.g., `add_memory` becomes `memory__add_memory`.
proxy_instance = create_proxy(proxy_config)
# Empty namespace to preserve dict keys as prefixes
mcp.mount(proxy_instance, namespace="")


# =====================================================================
# 4. DISCOVERY & GATEKEEPING TOOLS
# =====================================================================

@mcp.tool()
def get_allowed_services(agent_id: str) -> str:
    """
    Check which downstream services and tools an agent is authorized to use.
    Agents should call this first to discover their allowed environment.

    Args:
        agent_id: The unique identifier or token of the agent.
    """
    roles = AGENT_PERMISSIONS.get(agent_id)
    if roles is None:
        return json.dumps({"error": "Agent ID not recognized. Access denied."})

    allowed_tools = []
    for role in roles:
        allowed_tools.extend(PERMISSION_TO_TOOLS.get(role, []))

    return json.dumps({
        "agent_id": agent_id,
        "roles": roles,
        "allowed_tools": allowed_tools,
        "instruction": "Only attempt to call the tools listed in 'allowed_tools'."
    })


@mcp.tool()
def verify_access(agent_id: str, tool_name: str) -> str:
    """
    Verify if a specific tool execution is permitted for a given agent.

    Args:
        agent_id: The unique identifier of the agent.
        tool_name: The exact name of the tool (e.g., 'memory__add_memory').
    """
    roles = AGENT_PERMISSIONS.get(agent_id, [])

    for role in roles:
        if tool_name in PERMISSION_TO_TOOLS.get(role, []):
            return f"ACCESS GRANTED: {agent_id} may execute {tool_name}"

    return f"ACCESS DENIED: {agent_id} lacks permission for {tool_name}"


# =====================================================================
# 5. SERVER ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    # The orchestrator listens on port 8001
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
