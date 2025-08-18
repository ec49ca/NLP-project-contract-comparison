"""
TODO: tool generator agent should not be accessible via mcp. it should be a purely backend process

Tool Generator Agent - Simplified Dynamic Tool Creation

This agent provides dynamic tool generation using a streamlined workflow that
routes queries based on complexity, eliminating the overcalling problem.

New Dynamic Flow:
1. Complexity Assessment (1 call)
2A. Simple Path: Direct Generation (1 call total)
2B. Complex Path: Analyze & Plan → Complete Solution (2-3 calls total)

Max API calls: 3 (vs 27 in original system)
"""

import logging
from typing import Dict, List, Any, Optional
from ...interfaces.agent import AgentInterface
from ...services.prompt_service import PromptService
from uuid import UUID
from openai import OpenAI
import os
import json
import re
import uuid
import datetime

logger = logging.getLogger(__name__)


class ToolGeneratorAgent(AgentInterface):
    """Simplified tool generator agent for dynamic tool creation"""

    def __init__(self):
        self._agent_id_str = "tool_generator"
        self._uuid = None
        self.agent_id = "tool_generator"
        self._name = "Tool Generator Agent"
        self._description = "Generates dynamic tools from natural language queries using simplified routing"
        self._initialized = False
        self.category = "tool_generation"
        self.status = "initialized"
        self._tools = {}
        self.client = None
        self.api_key = None

        # Simple in-memory storage
        self.pending_tools = {}
        self.approved_tools = {}

        # Debug logging setup
        self.debug_file = "logs/tool_generator_debug.log"
        self.current_session_id = str(uuid.uuid4())[:8]

    def log_debug(self, step: str, data: Any, step_type: str = "INFO"):
        """Log debug information to file for development"""
        try:
            timestamp = datetime.datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "session_id": self.current_session_id,
                "step": step,
                "type": step_type,
                "data": data if isinstance(data, (str, dict, list)) else str(data),
            }

            with open(self.debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(
                    f"[{timestamp}] SESSION: {self.current_session_id} | {step_type}: {step}\n"
                )
                f.write(f"{'='*80}\n")
                if isinstance(data, dict) or isinstance(data, list):
                    f.write(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    f.write(str(data))
                f.write(f"\n{'='*80}\n\n")
        except Exception as e:
            logger.error("Debug logging failed", extra={'error': str(e)})

    def execute_code(
        self, code: str, data: List[Dict[str, Any]], kwargs: Dict[str, Any]
    ) -> Any:
        """Execute generated Python code with data and kwargs"""
        try:
            # Create safe environment with pandas available
            import pandas as pd

            safe_globals = {
                "__builtins__": {
                    "len": len,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "range": range,
                    "list": list,
                    "dict": dict,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                },
                "pd": pd,
            }

            local_vars = {}
            exec(code, safe_globals, local_vars)

            # Find the function (should be 'generated_function')
            func = local_vars.get("generated_function")
            if not func:
                # Fallback to first function found
                func = next(iter(local_vars.values()))

            # Convert data to pandas DataFrame if it's a list of dicts
            if isinstance(data, list) and data and isinstance(data[0], dict):
                data_df = pd.DataFrame(data)
            else:
                data_df = data

            # Execute the function
            return func(data_df, kwargs)
        except Exception as e:
            return f"Error: {str(e)}"

    def extract_kwargs_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract kwargs from function response"""
        try:
            # Look for kwargs in comments
            kwargs_match = re.search(
                r"# KWARGS NEEDED:(.*?)(?=\n#|\n\n|\Z)", response_text, re.DOTALL
            )
            if not kwargs_match:
                return {}

            kwargs_text = kwargs_match.group(1).strip()
            kwargs = {}

            # Parse kwargs from comments
            for line in kwargs_text.split("\n"):
                line = line.strip()
                if line.startswith("#") and ":" in line:
                    line = line[1:].strip()  # Remove leading #
                    if ":" in line:
                        key, desc = line.split(":", 1)
                        key = key.strip()
                        # Generate sample value based on key name
                        if "threshold" in key.lower():
                            kwargs[key] = 0
                        elif "field" in key.lower():
                            kwargs[key] = "field_name"
                        elif "category" in key.lower():
                            kwargs[key] = "category"
                        else:
                            kwargs[key] = "value"

            return kwargs
        except Exception as e:
            logger.error("Error extracting kwargs", extra={'error': str(e)})
            return {}

    @property
    def agent_id_str(self) -> str:
        return self._agent_id_str

    @property
    def uuid(self) -> UUID:
        if self._uuid is None:
            raise ValueError("UUID has not been set yet.")
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID):
        if self._uuid is not None:
            raise ValueError("UUID can only be set once.")
        self._uuid = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        try:
            self.api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not found in config or environment")

            self.client = OpenAI(api_key=self.api_key)
            self._initialized = True
            logger.info("ToolGeneratorAgent initialized successfully")
        except Exception as e:
            logger.error("Error initializing ToolGeneratorAgent", extra={'error': str(e)})
            raise e

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
        if not self._initialized or not self.client:
            return {"error": "Agent not initialized"}

        command = request.get("command", "")

        if command == "generate_and_execute":
            return await self._generate_and_execute(request)
        elif command == "assess_complexity":
            return await self._assess_complexity(request)
        elif command == "generate_direct":
            return await self._generate_direct(request)
        elif command == "analyze_and_plan":
            return await self._analyze_and_plan(request)
        elif command == "generate_complete_solution":
            return await self._generate_complete_solution(request)
        elif command == "get_pending_tools":
            return await self._get_pending_tools(request)
        elif command == "approve_tool":
            return await self._approve_tool(request)
        elif command == "reject_tool":
            return await self._reject_tool(request)
        elif command == "get_approved_tools":
            return await self._get_approved_tools(request)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "generate_and_execute",
                    "assess_complexity",
                    "generate_direct",
                    "analyze_and_plan",
                    "generate_complete_solution",
                    "get_pending_tools",
                    "approve_tool",
                    "reject_tool",
                    "get_approved_tools",
                ],
            }

    async def _assess_complexity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Assess query complexity to determine routing"""
        try:
            query = request.get("query", "")
            data = request.get("data", [])

            if not query:
                return {"error": "Missing query parameter"}

            self.log_debug(
                "COMPLEXITY_ASSESSMENT_START",
                {"query": query, "data_length": len(data)},
                "STEP_START",
            )

            # Get complexity assessment prompt
            prompt_data = PromptService.get_complexity_assessment_prompt(query, data)

            # Make GPT-4 call
            assert self.client is not None, "Client not initialized"
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_data["system"]},
                    {"role": "user", "content": prompt_data["user"]},
                ],
                temperature=0.0,
            )

            raw_response = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                assessment = json.loads(raw_response)
            except json.JSONDecodeError:
                # Fallback parsing
                assessment = {
                    "complexity": "COMPLEX",
                    "reasoning": "Failed to parse response, defaulting to complex",
                    "operations": ["unknown"],
                    "dependencies": "Unknown",
                }

            self.log_debug(
                "COMPLEXITY_ASSESSMENT_COMPLETE",
                {"assessment": assessment, "raw_response": raw_response},
                "STEP_COMPLETE",
            )

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "complexity": assessment["complexity"],
                    "reasoning": assessment["reasoning"],
                    "operations": assessment["operations"],
                    "dependencies": assessment["dependencies"],
                },
            }

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Error assessing complexity: {str(e)}",
            }
            self.log_debug("COMPLEXITY_ASSESSMENT_ERROR", error_result, "ERROR")
            logger.error("Error assessing complexity", extra={'error': str(e)})
            return error_result

    async def _generate_direct(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2A: Direct generation for simple queries"""
        try:
            query = request.get("query", "")
            data = request.get("data", [])

            if not query:
                return {"error": "Missing query parameter"}

            self.log_debug(
                "DIRECT_GENERATION_START",
                {"query": query, "data_length": len(data)},
                "STEP_START",
            )

            # Get direct generation prompt
            prompt_data = PromptService.get_direct_generation_prompt(query, data)

            # Make GPT-4 call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_data["system"]},
                    {"role": "user", "content": prompt_data["user"]},
                ],
                temperature=0.0,
            )

            raw_code = response.choices[0].message.content.strip()

            # Clean code (remove markdown formatting)
            function_code = re.sub(r"```(?:python)?\n?", "", raw_code).strip("`")

            # Extract kwargs from the response
            kwargs = self.extract_kwargs_from_response(raw_code)

            # Execute the function to test it
            output = self.execute_code(function_code, data, kwargs)

            self.log_debug(
                "DIRECT_GENERATION_COMPLETE",
                {"function_code": function_code, "kwargs": kwargs, "output": output},
                "STEP_COMPLETE",
            )

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "function_code": function_code,
                    "kwargs": kwargs,
                    "output": output,
                    "metadata": {
                        "intent_summary": query,
                        "capabilities": ["direct_generation"],
                        "tags": ["simple", "direct"],
                    },
                },
            }

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Error in direct generation: {str(e)}",
            }
            self.log_debug("DIRECT_GENERATION_ERROR", error_result, "ERROR")
            logger.error("Error in direct generation", extra={'error': str(e)})
            return error_result

    async def _analyze_and_plan(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2B: Analyze complex query and create execution plan"""
        try:
            query = request.get("query", "")
            data = request.get("data", [])

            if not query:
                return {"error": "Missing query parameter"}

            self.log_debug(
                "ANALYZE_AND_PLAN_START",
                {"query": query, "data_length": len(data)},
                "STEP_START",
            )

            # Get analysis prompt
            prompt_data = PromptService.get_analyze_and_plan_prompt(query, data)

            # Make GPT-4 call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_data["system"]},
                    {"role": "user", "content": prompt_data["user"]},
                ],
                temperature=0.0,
            )

            raw_response = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                analysis = json.loads(raw_response)
            except json.JSONDecodeError:
                # Fallback analysis
                analysis = {
                    "understanding": "Complex query requiring multi-step analysis",
                    "components": [
                        {
                            "operation": "Unknown",
                            "purpose": "Analysis failed",
                            "input": "data",
                            "output": "result",
                        }
                    ],
                    "data_flow": "Unknown",
                    "edge_cases": ["Parse error"],
                    "solution_approach": "Generate holistic solution",
                }

            self.log_debug(
                "ANALYZE_AND_PLAN_COMPLETE",
                {"analysis": analysis, "raw_response": raw_response},
                "STEP_COMPLETE",
            )

            return {
                "status": "success",
                "data": {"success": True, "analysis": analysis},
            }

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Error in analyze and plan: {str(e)}",
            }
            self.log_debug("ANALYZE_AND_PLAN_ERROR", error_result, "ERROR")
            logger.error("Error in analyze and plan", extra={'error': str(e)})
            return error_result

    async def _generate_complete_solution(
        self, request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 3: Generate complete solution for complex queries"""
        try:
            query = request.get("query", "")
            data = request.get("data", [])
            analysis = request.get("analysis", {})

            if not query:
                return {"error": "Missing query parameter"}

            self.log_debug(
                "COMPLETE_SOLUTION_START",
                {"query": query, "data_length": len(data), "analysis": analysis},
                "STEP_START",
            )

            # Get complete solution prompt
            prompt_data = PromptService.get_complete_solution_prompt(
                query, data, analysis
            )

            # Make GPT-4 call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_data["system"]},
                    {"role": "user", "content": prompt_data["user"]},
                ],
                temperature=0.0,
            )

            raw_code = response.choices[0].message.content.strip()

            # Clean code (remove markdown formatting)
            function_code = re.sub(r"```(?:python)?\n?", "", raw_code).strip("`")

            # Extract kwargs from the response
            kwargs = self.extract_kwargs_from_response(raw_code)

            # Execute the function to test it
            output = self.execute_code(function_code, data, kwargs)

            self.log_debug(
                "COMPLETE_SOLUTION_COMPLETE",
                {"function_code": function_code, "kwargs": kwargs, "output": output},
                "STEP_COMPLETE",
            )

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "function_code": function_code,
                    "kwargs": kwargs,
                    "output": output,
                    "metadata": {
                        "intent_summary": analysis.get("understanding", query),
                        "capabilities": ["complex_analysis", "multi_step"],
                        "tags": ["complex", "holistic"],
                    },
                },
            }

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Error in complete solution: {str(e)}",
            }
            self.log_debug("COMPLETE_SOLUTION_ERROR", error_result, "ERROR")
            logger.error("Error in complete solution", extra={'error': str(e)})
            return error_result

    async def _generate_and_execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Complete simplified workflow: assess → route → generate"""
        try:
            query = request.get("query", "")
            data = request.get("data", [])

            self.log_debug(
                "GENERATE_AND_EXECUTE_START",
                {
                    "query": query,
                    "data_length": len(data),
                    "session_id": self.current_session_id,
                },
                "WORKFLOW_START",
            )

            if not query:
                return {"error": "Missing query parameter"}

            if not data:
                return {"error": "Missing data parameter"}

            # Step 1: Assess complexity
            complexity_result = await self._assess_complexity(
                {"query": query, "data": data}
            )
            if complexity_result.get("status") != "success":
                return complexity_result

            complexity = complexity_result["data"]["complexity"]

            # Route based on complexity
            if complexity == "SIMPLE":
                # Step 2A: Direct generation
                self.log_debug("ROUTING_SIMPLE", {"complexity": complexity}, "ROUTING")
                generation_result = await self._generate_direct(
                    {"query": query, "data": data}
                )
            else:
                # Step 2B: Complex path
                self.log_debug("ROUTING_COMPLEX", {"complexity": complexity}, "ROUTING")

                # Step 2B.1: Analyze and plan
                analysis_result = await self._analyze_and_plan(
                    {"query": query, "data": data}
                )
                if analysis_result.get("status") != "success":
                    return analysis_result

                analysis = analysis_result["data"]["analysis"]

                # Step 2B.2: Generate complete solution
                generation_result = await self._generate_complete_solution(
                    {"query": query, "data": data, "analysis": analysis}
                )

            if generation_result.get("status") != "success":
                return generation_result

            # Save to pending storage
            tool_id = str(uuid.uuid4())
            tool_entry = {
                "id": tool_id,
                "query": query,
                "complexity": complexity,
                "function_code": generation_result["data"]["function_code"],
                "kwargs": generation_result["data"]["kwargs"],
                "output": generation_result["data"]["output"],
                "metadata": generation_result["data"]["metadata"],
                "created_at": datetime.datetime.now().isoformat(),
            }

            self.pending_tools[tool_id] = tool_entry

            self.log_debug(
                "STORAGE_SAVE",
                {
                    "tool_id": tool_id,
                    "storage_location": "self.pending_tools (in-memory)",
                },
                "STORAGE",
            )

            # Try to write to file
            try:
                tool_filename = f"generated_tools/generated_tool_{self.current_session_id}_{tool_id[:8]}.json"
                function_filename = f"generated_tools/generated_function_{self.current_session_id}_{tool_id[:8]}.py"

                with open(tool_filename, "w", encoding="utf-8") as f:
                    json.dump(tool_entry, f, indent=2, ensure_ascii=False)

                with open(function_filename, "w", encoding="utf-8") as f:
                    f.write(generation_result["data"]["function_code"])

                self.log_debug(
                    "FILE_OUTPUT_SUCCESS",
                    {
                        "tool_filename": tool_filename,
                        "function_filename": function_filename,
                    },
                    "FILE_OUTPUT",
                )

            except Exception as e:
                self.log_debug(
                    "FILE_OUTPUT_ERROR",
                    {
                        "error": str(e),
                        "tool_filename": f"generated_tools/generated_tool_{self.current_session_id}_{tool_id[:8]}.json",
                        "function_filename": f"generated_tools/generated_function_{self.current_session_id}_{tool_id[:8]}.py",
                    },
                    "ERROR",
                )

            result = {
                "status": "success",
                "data": {
                    "success": True,
                    "tool_id": tool_id,
                    "complexity": complexity,
                    "function_code": generation_result["data"]["function_code"],
                    "kwargs": generation_result["data"]["kwargs"],
                    "output": generation_result["data"]["output"],
                    "metadata": generation_result["data"]["metadata"],
                    "api_calls_used": 2 if complexity == "SIMPLE" else 3,
                    "files_created": {
                        "tool_data": f"generated_tools/generated_tool_{self.current_session_id}_{tool_id[:8]}.json",
                        "function_code": f"generated_tools/generated_function_{self.current_session_id}_{tool_id[:8]}.py",
                    },
                },
            }

            self.log_debug("GENERATE_AND_EXECUTE_COMPLETE", result, "WORKFLOW_COMPLETE")
            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"Error in generate and execute: {str(e)}",
            }
            self.log_debug("GENERATE_AND_EXECUTE_ERROR", error_result, "ERROR")
            logger.error("Error in generate and execute", extra={'error': str(e)})
            return error_result

    async def _get_pending_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get all pending tools awaiting approval"""
        try:
            return {
                "status": "success",
                "data": {
                    "success": True,
                    "pending_tools": list(self.pending_tools.values()),
                    "count": len(self.pending_tools),
                },
            }
        except Exception as e:
            logger.error("Error getting pending tools", extra={'error': str(e)})
            return {
                "status": "error",
                "message": f"Error getting pending tools: {str(e)}",
            }

    async def _approve_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Approve a pending tool"""
        try:
            tool_id = request.get("tool_id", "")

            if not tool_id:
                return {"error": "Missing tool_id parameter"}

            if tool_id not in self.pending_tools:
                return {"error": f"Tool {tool_id} not found in pending tools"}

            # Move from pending to approved
            tool_entry = self.pending_tools.pop(tool_id)
            tool_entry["approved_at"] = datetime.datetime.now().isoformat()
            self.approved_tools[tool_id] = tool_entry

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "message": f"Tool {tool_id} approved successfully",
                    "approved_tool": tool_entry,
                },
            }

        except Exception as e:
            logger.error("Error approving tool", extra={'error': str(e)})
            return {"status": "error", "message": f"Error approving tool: {str(e)}"}

    async def _reject_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Reject a pending tool"""
        try:
            tool_id = request.get("tool_id", "")
            reason = request.get("reason", "No reason provided")

            if not tool_id:
                return {"error": "Missing tool_id parameter"}

            if tool_id not in self.pending_tools:
                return {"error": f"Tool {tool_id} not found in pending tools"}

            # Remove from pending
            tool_entry = self.pending_tools.pop(tool_id)
            tool_entry["rejected_at"] = datetime.datetime.now().isoformat()
            tool_entry["rejection_reason"] = reason

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "message": f"Tool {tool_id} rejected successfully",
                    "rejected_tool": tool_entry,
                },
            }

        except Exception as e:
            logger.error("Error rejecting tool", extra={'error': str(e)})
            return {"status": "error", "message": f"Error rejecting tool: {str(e)}"}

    async def _get_approved_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get all approved tools"""
        try:
            return {
                "status": "success",
                "data": {
                    "success": True,
                    "approved_tools": list(self.approved_tools.values()),
                    "count": len(self.approved_tools),
                },
            }
        except Exception as e:
            logger.error("Error getting approved tools", extra={'error': str(e)})
            return {
                "status": "error",
                "message": f"Error getting approved tools: {str(e)}",
            }

    async def shutdown(self) -> None:
        """Shutdown the agent."""
        logger.info("ToolGeneratorAgent shutting down")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get agent capabilities."""
        return [
            {
                "name": "generate_and_execute",
                "description": "Complete workflow: assess complexity and generate appropriate solution",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query",
                    },
                    "data": {"type": "array", "description": "JSON dataset to analyze"},
                },
            },
            {
                "name": "assess_complexity",
                "description": "Assess query complexity for routing",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query",
                    },
                    "data": {"type": "array", "description": "JSON dataset sample"},
                },
            },
            {
                "name": "generate_direct",
                "description": "Direct generation for simple queries",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Simple natural language query",
                    },
                    "data": {"type": "array", "description": "JSON dataset to analyze"},
                },
            },
            {
                "name": "analyze_and_plan",
                "description": "Analyze complex queries and create execution plan",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Complex natural language query",
                    },
                    "data": {"type": "array", "description": "JSON dataset sample"},
                },
            },
            {
                "name": "generate_complete_solution",
                "description": "Generate complete solution for complex queries",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query",
                    },
                    "data": {"type": "array", "description": "JSON dataset to analyze"},
                    "analysis": {
                        "type": "object",
                        "description": "Analysis from analyze_and_plan",
                    },
                },
            },
            {
                "name": "get_pending_tools",
                "description": "Get all pending tools awaiting approval",
                "parameters": {},
            },
            {
                "name": "approve_tool",
                "description": "Approve a pending tool",
                "parameters": {
                    "tool_id": {"type": "string", "description": "Tool ID to approve"}
                },
            },
            {
                "name": "reject_tool",
                "description": "Reject a pending tool",
                "parameters": {
                    "tool_id": {"type": "string", "description": "Tool ID to reject"},
                    "reason": {"type": "string", "description": "Reason for rejection"},
                },
            },
            {
                "name": "get_approved_tools",
                "description": "Get all approved tools",
                "parameters": {},
            },
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "initialized": self._initialized,
            "pending_tools_count": len(self.pending_tools),
            "approved_tools_count": len(self.approved_tools),
            "session_id": self.current_session_id,
            "capabilities_count": len(self.get_tools()),
        }
