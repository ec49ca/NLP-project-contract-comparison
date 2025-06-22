"""
Tool endpoints for the MCP HTTP API

Contains all tool-related endpoints including discovery and invocation.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from ..models.requests import ToolDiscoveryRequest, ToolInvocationRequest
from ..util.dependencies import get_initialized_server, get_agents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/discover")
async def discover_tools(
    request: ToolDiscoveryRequest,
    _: bool = Depends(get_initialized_server)
):
    """Discover available tools"""
    try:
        agents = get_agents()
        discovered_tools = []

        # If agent_id is specified, only get tools from that agent
        target_agents = {request.agent_id: agents[request.agent_id]} if request.agent_id and request.agent_id in agents else agents

        for agent_id, agent in target_agents.items():
            if not agent.is_initialized:
                continue

            tools = await agent.get_tools()

            for tool in tools:
                # Apply filter if provided
                if request.filter:
                    # Simple filtering logic - can be enhanced
                    if 'name' in request.filter:
                        if request.filter['name'].lower() not in tool.name.lower():
                            continue

                discovered_tools.append({
                    "agent_id": agent_id,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                    "category": getattr(agent, 'category', 'general')
                })

        return {"success": True, "data": discovered_tools}

    except Exception as e:
        logger.error(f"Error discovering tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoke")
async def invoke_tool(
    request: ToolInvocationRequest,
    _: bool = Depends(get_initialized_server)
):
    """Invoke a specific tool"""
    try:
        agents = get_agents()

        if request.agent_id not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")

        agent = agents[request.agent_id]
        if not agent.is_initialized:
            raise HTTPException(status_code=503, detail=f"Agent {request.agent_id} not initialized")

        # Execute the tool
        result = await agent.execute_tool(request.tool_name, request.arguments)

        return {
            "success": True,
            "data": {
                "agent_id": request.agent_id,
                "tool_name": request.tool_name,
                "result": result,
                "session_id": request.session_id
            }
        }

    except Exception as e:
        logger.error(f"Error invoking tool {request.tool_name} on agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))