"""
Agent endpoints for the MCP HTTP API

Contains all agent-related endpoints including discovery and invocation.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from ..models.requests import AgentDiscoveryRequest, AgentInvocationRequest
from ..util.dependencies import get_initialized_server, get_agents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/discover")
async def discover_agents(
	request: AgentDiscoveryRequest,
	_: bool = Depends(get_initialized_server)
):
	"""Discover available agents"""
	try:
		agents = get_agents()
		discovered_agents = []
		for agent_id, agent in agents.items():
			if not agent.is_initialized:
				continue

			# Apply filter if provided
			if request.filter:
				# Simple filtering logic - can be enhanced
				if 'category' in request.filter:
					if hasattr(agent, 'category') and agent.category != request.filter['category']:
						continue

			agent_info = agent.get_agent_info()
			tools = await agent.get_tools()

			# add discovered agents with tool list comprehension
			discovered_agents.append({
				"id": agent_id,
				"name": agent_info['name'],
				"description": agent_info['description'],
				"category": agent_info['category'],
				"tools": [
					{
						"name": tool.name,
						"description": tool.description,
						"input_schema": tool.inputSchema
					}
					for tool in tools
				],
				"status": "active"
			})

		return {"success": True, "data": discovered_agents}

	# TODO: add more robust error handling
	except Exception as e:
		logger.error(f"Error discovering agents: {e}")
		raise HTTPException(status_code=500, detail=str(e))



"""
1. Requires agent_id -> uses for lookup + validates agent exists
2. Calls agent.execute with input data and context
TODO: 3. Implementing this flow for KG later -Sohum
"""
@router.post("/invoke")
async def invoke_agent(
	request: AgentInvocationRequest,
	_: bool = Depends(get_initialized_server)
):
	"""Invoke an agent"""
	try:
		agents = get_agents()

		if request.agent_id not in agents:
			raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")

		agent = agents[request.agent_id]
		if not agent.is_initialized:
			raise HTTPException(status_code=503, detail=f"Agent {request.agent_id} not initialized")

		# Execute the agent
		result = await agent.execute(request.input_data, request.context or {})

		return {
			"success": True,
			"data": {
				"agent_id": request.agent_id,
				"result": result,
				"session_id": request.session_id
			}
		}

	except Exception as e:
		logger.error(f"Error invoking agent {request.agent_id}: {e}")
		raise HTTPException(status_code=500, detail=str(e))
