"""
Meta Agent - Intent Analysis and Execution Planning

The MetaAgent class serves as the central coordinator for analyzing user intent and creating
execution plans. It acts as the "brain" of the multi-agent system by:

1. **Intent Analysis**: Analyzes user queries to determine their intent (e.g., search,
   general inquiry, specific task) and extracts relevant entities.

2. **Execution Planning**: Creates step-by-step execution plans that coordinate multiple
   agents to fulfill the user's request efficiently.

3. **Tool Coordination**: Provides tools for intent analysis and plan creation that can
   be used by other agents or the main system.

Usage:
    The MetaAgent is typically invoked first in a multi-agent workflow to:
    - Understand what the user wants to accomplish
    - Create a roadmap for how to achieve it
    - Coordinate the execution across specialized agents

Example:
    meta_agent = MetaAgent()
    result = await meta_agent.execute({
        "query": "Search for information about machine learning"
    }, {})
    # Returns intent analysis and execution plan
"""

from typing import Dict, List, Any
from .base_agent import BaseAgent, Tool

class MetaAgent(BaseAgent):
    """Meta agent for analyzing user intent and creating execution plans"""

    def __init__(self):
        super().__init__("meta")
        self.name = "Meta Agent"
        self.description = "Analyzes user intent and creates chain-of-thought execution plans"
        self.category = "analysis"

    async def get_tools(self) -> List[Tool]:
        """Get the tools provided by this agent"""
        return [
            Tool(
                name="analyze_intent",
                description="Analyze user queries to determine intent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "User query to analyze"}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="create_execution_plan",
                description="Create step-by-step execution plans",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string", "description": "Analyzed intent"},
                        "context": {"type": "object", "description": "Additional context"}
                    },
                    "required": ["intent"]
                }
            )
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a specific tool"""
        if tool_name == "analyze_intent":
            query = arguments.get("query", "")
            # Placeholder implementation
            return {
                "intent": "search" if "search" in query.lower() else "general",
                "confidence": 0.8,
                "entities": []
            }

        elif tool_name == "create_execution_plan":
            intent = arguments.get("intent", "general")
            # Placeholder implementation
            return {
                "plan": [
                    {"step": 1, "action": "analyze_query", "agent": "meta"},
                    {"step": 2, "action": "execute_search", "agent": "vector_search"},
                    {"step": 3, "action": "format_results", "agent": "meta"}
                ],
                "estimated_time": "5 seconds"
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute the meta agent"""
        query = input_data.get("query", "")

        # Analyze intent
        intent_result = await self.execute_tool("analyze_intent", {"query": query})

        # Create execution plan
        plan_result = await self.execute_tool("create_execution_plan", {"intent": intent_result["intent"]})

        return {
            "intent_analysis": intent_result,
            "execution_plan": plan_result,
            "agent": "meta"
        }