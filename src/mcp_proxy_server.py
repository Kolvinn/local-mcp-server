import os
import json
from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.exceptions import FastMCPError

PORT = int(os.environ.get("MCP_PROXY_SERVER_PORT", 8000))

# =====================================================================
# 1. GATEKEEPER CONFIGURATION
# =====================================================================
# A static representation of an RBAC (Role-Based Access Control) system.
# In production, this would query a database or an auth service.
AGENT_PERMISSIONS = {
    "agent_alpha": ["sequential_thinking", "memory_read"],
    "agent_admin": ["sequential_thinking", "memory_read", "memory_write"],
    "guest": [],
}

# Map granular permissions to the actual underlying tool names
PERMISSION_TO_TOOLS = {
    "sequential_thinking": ["sequential_thinking__sequential_thinking"],
    "memory_read": [
        "memory__search_memory",
        "memory__list_projects",
        "memory__search_goal_nodes",
        "memory__get_goal_tree",
    ],
    "memory_write": [
        "memory__add_memory",
        "memory__delete_memory",
        "memory__sync_metadata",
        "memory__add_goal_node",
        "memory__update_goal_node",
        "memory__delete_goal_node",
    ],
    "memory_admin": [
        "memory__search_goal_nodes",
        "memory__get_goal_tree",
        "memory__add_goal_node",
        "memory__update_goal_node",
        "memory__delete_goal_node",
    ],
}


mcp = FastMCP("CompositeOrchestrator")


def mount_proxies(mcp: FastMCP):
    # =====================================================================
    # INDIVIDUAL PROXY MOUNTING (The Modular Way)
    # =====================================================================

    # 1. Mount Sequential Thinking
    try:
        seq_proxy = create_proxy(
            {
                "mcpServers": {
                    "sequential_thinking": {
                        "command": "bunx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-sequential-thinking",
                        ],
                    }
                }
            }
        )
        mcp.mount(
            seq_proxy, namespace=""
        )  # Namespace is empty to use the dict key prefix[cite: 1]
    except Exception as e:
        print(f"Failed to mount Sequential Thinking: {e}")

    # 2. Mount Memory Server (with persistence fix)
    try:
        mem_proxy = create_proxy(
            {
                "mcpServers": {
                    "memory": {
                        "command": "python",
                        "args": ["/home/dev/app/src/memory_service.py"],
                        "env": {
                            "PYTHONUNBUFFERED": "1"
                        },  # Ensures stdio persistence[cite: 1]
                    }
                }
            }
        )
        mcp.mount(mem_proxy, namespace="")
        
    except Exception as e:
        print(f"Failed to mount Memory Server: {e}")

     # 2. Mount Memory Server (with persistence fix)
    try:
        firecrawl = create_proxy(
            {
                {
  "mcpServers": {
    "firecrawl-mcp": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "your-self-hosted-key",
        "FIRECRAWL_API_URL": "http://localhost:3000"
      }
    }
  }
}

            }
        )
        mcp.mount(mem_proxy, namespace="")
        
    except Exception as e:
        print(f"Failed to mount Memory Server: {e}")


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

    return json.dumps(
        {
            "agent_id": agent_id,
            "roles": roles,
            "allowed_tools": allowed_tools,
            "instruction": "Only attempt to call the tools listed in 'allowed_tools'.",
        }
    )


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
    # The orchestrator listens on the configured port (default: 8000)
    mount_proxies(mcp)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
