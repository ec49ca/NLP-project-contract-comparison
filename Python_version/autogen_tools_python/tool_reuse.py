import json
from typing import Dict, Any, List, Optional

from .storage import retrieve_agents
from .runner import execute_agent
from .utils import get_field_value_map, describe_field_schema

async def find_and_execute_existing_tool(
    query: str,
    data: List[Dict[str, Any]],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Find and execute an existing tool that matches the query.
    """
    try:
        # Get all available agents
        agents = retrieve_agents()
        
        if not agents:
            return {"result": None, "error": "No agents available"}
        
        # Simple similarity check - in a real implementation, you'd use embeddings
        # For now, we'll just check if any agent's description contains key words from the query
        query_words = set(query.lower().split())
        
        best_match = None
        best_score = 0
        
        for agent_name, agent_data in agents.items():
            description = agent_data.get("description", "").lower()
            description_words = set(description.split())
            
            # Simple word overlap score
            overlap = len(query_words.intersection(description_words))
            if overlap > best_score:
                best_score = overlap
                best_match = (agent_name, agent_data)
        
        # If we found a reasonable match (at least 2 words overlap)
        if best_match and best_score >= 2:
            agent_name, agent_data = best_match
            
            if verbose:
                print(f"🔄 Found existing tool: {agent_name}")
                print(f"📝 Description: {agent_data.get('description', 'No description')}")
            
            # Extract kwargs from the stored agent
            kwargs_str = agent_data.get("kwargs_ex", "{}")
            try:
                kwargs = json.loads(kwargs_str)
            except:
                kwargs = {}
            
            # Execute the agent
            result = await execute_agent(agent_name, data, kwargs)
            
            return {
                "result": {
                    "code": agent_data.get("code"),
                    "kwargs": kwargs,
                    "output": result,
                    "reused": True,
                    "agent_name": agent_name
                },
                "error": None
            }
        
        return {"result": None, "error": "No suitable existing tool found"}
        
    except Exception as error:
        return {"result": None, "error": str(error)} 