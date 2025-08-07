from re import I

from fastapi import HTTPException

from src.services.prompt_service import prompt_service

from ..registry.registry import AgentRegistrySystem
from ..discovery.agent_discovery import AgentDiscovery
import logging
from uuid import UUID
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MetaAgent:
    def __init__(self):
        self.agent_registry = AgentRegistrySystem()
        self.discovery = AgentDiscovery()
        self.agents = None
        self.tools = {}

    # implement refreshes for agents/tools. not necessary right now

    """
	/mcp/agents should return:
	{
		"total_agents": 1,
		"active_agents": 1,
		"agents": [
			{
				"id": "Agent1",
				"name": "Agent 1",
				"description": "Description of Agent 1",

				OPTIONAL:
				"tools": [
					{
						"name": "Tool 1",
						"description": "Description of Tool 1",
						"parameters": {}
					}
				],
				"tags": [
					"tag1",
					"tag2"
				],
				"isActive": true,
				"agentType": "agentType1"
			}
		]
	}
	"""

    async def get_agents(self):
        if self.agents is None:
            self.agents = await self.agent_registry.get_registry_state()
        else:
            return self.agents
        return self.agents

    """
	returns:
	{
		"tools": [
			{
				# means not used right now
				# "agentId": "Agent1 ID",
				# "id": "Tool1",
				"name": "Tool 1",
				"description": "Description of Tool 1",
				"parameters": {
					"parameter1": "description of parameter 1",
					"parameter2": "description of parameter 2"
				},
				"returnValues": {
					"description": "Description of what this tool returns",
					"structure": {
						"field1": "type - description of field1",
						"field2": "type - description of field2"
					}
				}

				OPTIONAL:
				metadata: {
					"metadata1": "description of metadata 1",
				},
				tags: [
					"tag1",
					"tag2"
				],
			}
		]
	}
	"""

    async def get_tools_for_agent(self, agent_id):
        try:
            if self.tools.get(agent_id) is None:
                if self.agents is None:
                    self.agents = await self.agent_registry.get_registry_state()

                agent_tools = self.agents["agents"].get(agent_id).get("tools")
                self.tools[agent_id] = agent_tools
                return agent_tools
            else:
                return self.tools[agent_id]

        except Exception as e:
            logger.error(f"Error getting tools for agent {agent_id}: {e}")
            return []

    # query has information about what orchestrator wants meta_agent -> agent to do
    async def handle_execute_tool_via_agent_request(self, agent_id, query):
        print(f"Executing {agent_id} with query {query}")

        # make llm call to format query
        # query should be reasoning for how to use agent and data that neesd to be included
        # agent = await self.agent_registry.get_agent(UUID(agent_id))
        available_tools = await self.get_tools_for_agent(agent_id)

        available_tools_str = ""
        for i in range(len(available_tools)):
            available_tools_str += f"{i+1}. {available_tools[i]['name']}: {available_tools[i]['description']}\n"
            available_tools_str += f"Parameters: {available_tools[i]['parameters']}\n"
            available_tools_str += "\n\n"

        return available_tools_str

        prompts = prompt_service.get_meta_agent_handle_agent_request_prompt(
            available_tools_str, query
        )

        return prompts

        llm_service = LLMService()

        system_prompt = prompts.get("system_prompt")
        user_prompt = prompts.get("user_prompt")
        # llm response has the json
        llm_response = await llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request},
            ]
        )

        return
