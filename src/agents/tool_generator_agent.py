"""
Tool Generator Agent - Dynamic Tool Creation and Execution

This agent provides dynamic tool generation capabilities starting with query analysis and task graph creation.
Additional tools to be implemented:

## Core Tools to Implement:

1. **Core Workflow Steps**
   - analyze_query - PROMPT 1: Break down complex queries
   - create_task_graph - PROMPT 2: Convert steps to task graph
   - generate_single_tool - PROMPTS 4-7: Generate individual tools
   - execute_task_graph - PROMPT 3: Execute task graphs step by step
   - merge_task_graph - PROMPT 8: Merge into optimized function

2. **Complete Workflow**
   - generate_and_execute - Complete end-to-end workflow

3. **Tool Management**
   - get_pending_tools - List pending tools
   - approve_tool - Approve pending tools
   - reject_tool - Reject pending tools
   - get_approved_tools - List approved tools
"""

import logging
from typing import Dict, List, Any, Optional
from ..interfaces.agent import AgentInterface
from ..services.prompt_service import PromptService
from uuid import UUID
from openai import OpenAI
import os
import json
import re
import uuid
import datetime

logger = logging.getLogger(__name__)

class ToolGeneratorAgent(AgentInterface):
	"""Tool generator agent for dynamic tool creation and execution"""

	def __init__(self):
		self._agent_id_str = "tool_generator"
		self._uuid = None
		self._name = "Tool Generator Agent"
		self._description = "Generates and executes dynamic tools from natural language queries"
		self._initialized = False
		self.category = "tool_generation"
		self.client = None
		self.api_key = None
		# Add simple in-memory storage
		self.pending_tools = {}
		self.approved_tools = {}

		# Debug logging setup
		self.debug_file = "tool_generator_debug.log"
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
				"data": data if isinstance(data, (str, dict, list)) else str(data)
			}

			with open(self.debug_file, "a", encoding="utf-8") as f:
				f.write(f"\n{'='*80}\n")
				f.write(f"[{timestamp}] SESSION: {self.current_session_id} | {step_type}: {step}\n")
				f.write(f"{'='*80}\n")
				if isinstance(data, dict) or isinstance(data, list):
					f.write(json.dumps(data, indent=2, ensure_ascii=False))
				else:
					f.write(str(data))
				f.write(f"\n{'='*80}\n\n")
		except Exception as e:
			logger.error(f"Debug logging failed: {str(e)}")

	def parse_task_graph(self, raw_text: str) -> List[Dict[str, Any]]:
		"""Convert GPT text output to structured task list"""
		tasks = []
		lines = raw_text.strip().split('\n')
		current_task = None

		for line in lines:
			line = line.strip()
			if re.match(r'^\d+\.\s*\(task\d+\)', line):
				if current_task:
					tasks.append(current_task)
				task_id_match = re.search(r'\(task\d+\)', line)
				if task_id_match:
					task_id = task_id_match.group(0)[1:-1]  # Remove ()
					query = re.sub(r'^\d+\.\s*\(task\d+\)\s*', '', line)
					current_task = {"id": task_id, "query": query, "depends_on": [], "output": None}
			elif line.startswith('# depends_on:') and current_task:
				deps = line.replace('# depends_on:', '').strip().split(',')
				current_task["depends_on"] = [d.strip() for d in deps if d.strip()]
			elif line.startswith('# output:') and current_task:
				current_task["output"] = line.replace('# output:', '').strip()

		if current_task:
			tasks.append(current_task)
		return tasks

	def get_field_schema(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
		"""Analyze JSON data structure and create simple schema"""
		if not data:
			return {}

		# Just take first record and list field names and types
		sample = data[0]
		return {field: type(value).__name__ for field, value in sample.items()}

	def generate_function_name(self, query: str) -> str:
		"""Generate a unique function name from query"""
		return f"tool_{abs(hash(query)) % 10000}"

	def execute_code(self, code: str, data: List[Dict[str, Any]], kwargs: Dict[str, Any]) -> Any:
		"""Execute generated Python code with data and kwargs"""
		try:
			# Create safe environment
			local_vars = {}
			exec(code, {"__builtins__": {}}, local_vars)

			# Find the function (first function defined)
			func = next(iter(local_vars.values()))

			# Execute it
			return func(data, kwargs)
		except Exception as e:
			return f"Error: {str(e)}"

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
		"""Agent's unique identifier."""
		return self._name

	@property
	def description(self) -> str:
		"""Brief description of the agent's purpose."""
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
			logger.error(f"Error initializing ToolGeneratorAgent: {str(e)}")
			raise e

	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process incoming requests through the agent."""
		if not self._initialized:
			return {"error": "Agent not initialized"}

		command = request.get("command", "")

		if command == "analyze_query":
			return await self._analyze_query(request)
		elif command == "create_task_graph":
			return await self._create_task_graph(request)
		elif command == "generate_single_tool":
			return await self._generate_single_tool(request)
		elif command == "execute_task_graph":
			return await self._execute_task_graph(request)
		elif command == "merge_task_graph":
			return await self._merge_task_graph(request)
		elif command == "generate_and_execute":
			return await self._generate_and_execute(request)
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
				"available_commands": ["analyze_query", "create_task_graph", "generate_single_tool", "execute_task_graph", "merge_task_graph", "generate_and_execute", "get_pending_tools", "approve_tool", "reject_tool", "get_approved_tools"]
			}

	async def _analyze_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""PROMPT 1: Break down complex query into sequential steps"""
		try:
			query = request.get("query", "")
			data = request.get("data", [])

			self.log_debug("ANALYZE_QUERY_START", {
				"query": query,
				"data_length": len(data),
				"data_sample": data[:2] if data else []
			}, "STEP_START")

			if not query:
				return {"error": "Missing query parameter"}

			# Get the prompt from PromptService
			prompt_data = PromptService.get_analyze_query_prompt(query, data)

			self.log_debug("ANALYZE_QUERY_PROMPT", {
				"system_prompt": prompt_data["system"],
				"user_prompt": prompt_data["user"]
			}, "PROMPT")

			# Make GPT-4 call
			response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "system", "content": prompt_data["system"]},
					{"role": "user", "content": prompt_data["user"]}
				],
				temperature=0.0
			)

			raw_steps_text = response.choices[0].message.content.strip()

			self.log_debug("ANALYZE_QUERY_RESPONSE", {
				"raw_steps_text": raw_steps_text
			}, "GPT_RESPONSE")

			result = {
				"status": "success",
				"data": {
					"success": True,
					"steps": raw_steps_text,
					"query": query
				}
			}

			self.log_debug("ANALYZE_QUERY_COMPLETE", result, "STEP_COMPLETE")
			return result

		except Exception as e:
			error_result = {
				"status": "error",
				"message": f"Error analyzing query: {str(e)}"
			}
			self.log_debug("ANALYZE_QUERY_ERROR", error_result, "ERROR")
			logger.error(f"Error analyzing query: {str(e)}")
			return error_result

	async def _create_task_graph(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""PROMPT 2: Convert steps into structured task graph"""
		try:
			steps = request.get("steps", "")
			data = request.get("data", [])

			if not steps:
				return {"error": "Missing steps parameter"}

			# Get the prompt from PromptService
			prompt_data = PromptService.get_create_task_graph_prompt(steps)

			# Make GPT-4 call
			response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "system", "content": prompt_data["system"]},
					{"role": "user", "content": prompt_data["user"]}
				],
				temperature=0.0
			)

			raw_task_text = response.choices[0].message.content.strip()

			# Parse the task graph using our new function
			task_graph = self.parse_task_graph(raw_task_text)

			# Build simple metadata
			task_metadata = {
				"task_count": len(task_graph),
				"task_ids": [task["id"] for task in task_graph],
				"has_dependencies": any(task["depends_on"] for task in task_graph)
			}

			return {
				"status": "success",
				"data": {
					"success": True,
					"task_graph": task_graph,
					"metadata": task_metadata,
					"raw_task_text": raw_task_text
				}
			}

		except Exception as e:
			logger.error(f"Error creating task graph: {str(e)}")
			return {
				"status": "error",
				"message": f"Error creating task graph: {str(e)}"
			}

	async def _generate_single_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""PROMPTS 4-7: Generate a single tool (POC → Generalize → Extract params → Metadata)"""
		try:
			query = request.get("query", "")
			data = request.get("data", [])

			if not query:
				return {"error": "Missing query parameter"}

			# TODO: Add helper functions to generate field_schema_summary, function_name, etc.
			# For now, use simplified versions
			field_schema_summary = self.get_field_schema(data)
			function_name = self.generate_function_name(query)

			# PROMPT 4: Generate POC code
			poc_prompt = PromptService.get_generate_poc_prompt(query, data, field_schema_summary, function_name)
			poc_response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "system", "content": poc_prompt["system"]},
					{"role": "user", "content": poc_prompt["user"]}
				],
				temperature=0.0
			)

			poc_code = poc_response.choices[0].message.content.strip()

			# TODO: Add code cleaning logic here (remove ```python markers, etc.)
			if poc_code.startswith("```"):
				poc_code = re.sub(r"```[a-z]*\n?", "", poc_code)
				poc_code = re.sub(r"```$", "", poc_code).strip()

			# PROMPT 5: Generalize POC code
			generalize_prompt = PromptService.get_generalize_function_prompt(poc_code, data, query)
			generalize_response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "system", "content": generalize_prompt["system"]},
					{"role": "user", "content": generalize_prompt["user"]}
				],
				temperature=0.0
			)

			generalized_output = generalize_response.choices[0].message.content.strip()

			# TODO: Add logic to extract generalized code and kwargs comment
			# For now, assume the entire response is the generalized code
			generalized_code = generalized_output

			# PROMPT 6: Extract runtime kwargs
			kwargs_prompt = PromptService.get_extract_parameters_prompt(
				query, generalized_code, json.dumps(data, indent=2), {}, {}
			)
			kwargs_response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "user", "content": kwargs_prompt}
				],
				temperature=0.0
			)

			kwargs_output = kwargs_response.choices[0].message.content.strip()

			# TODO: Add logic to parse kwargs JSON from response
			kwargs_dict = {}
			try:
				# Clean code block formatting
				kwargs_output = re.sub(r"```(?:json)?", "", kwargs_output)
				kwargs_output = re.sub(r"```", "", kwargs_output).strip()
				match = re.search(r"\{[\s\S]+\}", kwargs_output)
				if match:
					kwargs_output = match.group(0)
				kwargs_dict = json.loads(kwargs_output)
			except:
				kwargs_dict = {}

			# PROMPT 7: Generate metadata
			metadata_prompt = PromptService.get_generate_metadata_prompt(
				query, generalized_code, ["filtering", "aggregation", "transformation"], []
			)
			metadata_response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "user", "content": metadata_prompt}
				],
				temperature=0.0
			)

			metadata_output = metadata_response.choices[0].message.content.strip()

			# TODO: Add logic to parse metadata JSON from response
			metadata = {}
			try:
				if metadata_output.startswith("```"):
					metadata_output = metadata_output.replace("```json", "").replace("```", "").strip()
				metadata = json.loads(metadata_output)
			except:
				metadata = {"intent_summary": query, "capabilities": ["filtering"], "tags": []}

			# Execute the tool and get real output
			output = self.execute_code(generalized_code, data, kwargs_dict)

			return {
				"status": "success",
				"data": {
					"success": True,
					"code": generalized_code,
					"kwargs": kwargs_dict,
					"output": output,
					"metadata": metadata,
					"poc_code": poc_code
				}
			}

		except Exception as e:
			logger.error(f"Error generating single tool: {str(e)}")
			return {
				"status": "error",
				"message": f"Error generating single tool: {str(e)}"
			}

	async def _execute_task_graph(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""PROMPT 3: Execute task graph step by step (perceive + execute each task)"""
		try:
			task_graph = request.get("task_graph", [])
			data = request.get("data", [])

			if not task_graph:
				return {"error": "Missing task_graph parameter"}

			execution_state = {}
			current_data = data

			for task in task_graph:
				# Step 1: Rewrite query with context using voyager_perceive
				rewrite_prompt = PromptService.get_rewrite_task_query_prompt(
					task["id"], task["query"], task_graph, execution_state
				)

				rewrite_response = self.client.chat.completions.create(
					model="gpt-4o",
					messages=[
						{"role": "system", "content": rewrite_prompt["system"]},
						{"role": "user", "content": rewrite_prompt["user"]}
					],
					temperature=0.0
				)

				rewritten_query = rewrite_response.choices[0].message.content.strip()

				# Step 2: Generate tool for this task
				tool_result = await self._generate_single_tool({
					"query": rewritten_query,
					"data": current_data
				})

				if tool_result["status"] != "success":
					return tool_result

				# Step 3: Get the output (already executed in _generate_single_tool)
				tool_data = tool_result["data"]
				output = tool_data["output"]

				# Step 4: Store result in execution state
				execution_state[task["id"]] = output
				if task.get("output"):
					execution_state[task["output"]] = output

				# Step 5: Update current data for next task if output is a dataset
				if isinstance(output, list) and output:  # If it's a non-empty dataset
					current_data = output

			return {
				"status": "success",
				"data": {
					"success": True,
					"final_output": current_data,
					"execution_state": execution_state
				}
			}

		except Exception as e:
			logger.error(f"Error executing task graph: {str(e)}")
			return {
				"status": "error",
				"message": f"Error executing task graph: {str(e)}"
			}

	async def _merge_task_graph(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""PROMPT 8: Merge task graph into single optimized function"""
		try:
			task_graph = request.get("task_graph", [])
			original_query = request.get("original_query", "")

			if not task_graph:
				return {"error": "Missing task_graph parameter"}

			# Get the prompt from PromptService
			prompt_data = PromptService.get_merge_tasks_prompt(task_graph, original_query)

			# Make GPT-4 call
			response = self.client.chat.completions.create(
				model="gpt-4o",
				messages=[
					{"role": "system", "content": prompt_data["system"]},
					{"role": "user", "content": prompt_data["user"]}
				],
				temperature=0.0
			)

			raw_code = response.choices[0].message.content.strip()

			# TODO: Add code cleaning logic here
			merged_code = re.sub(r"```(?:python)?\n?", "", raw_code).strip("`")

			# TODO: Add validation logic here
			if "def merged_function" not in merged_code:
				logger.warning("LLM did not generate a valid merged function")
				merged_code = "def merged_function(data):\n    # Error in generation\n    return []"

			# TODO: Add logic to test merged function
			# For now, return metadata placeholder
			metadata = {
				"originalTaskCount": len(task_graph),
				"mergedFunctionName": "merged_function",
				"dependenciesResolved": [t.get('id', '') for t in task_graph]
			}

			return {
				"status": "success",
				"data": {
					"success": True,
					"merged_code": merged_code,
					"metadata": metadata
				}
			}

		except Exception as e:
			logger.error(f"Error merging task graph: {str(e)}")
			return {
				"status": "error",
				"message": f"Error merging task graph: {str(e)}"
			}

	async def _generate_and_execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Complete end-to-end workflow: analyze → plan → generate → execute → merge"""
		try:
			query = request.get("query", "")
			data = request.get("data", [])

			self.log_debug("GENERATE_AND_EXECUTE_START", {
				"query": query,
				"data_length": len(data),
				"session_id": self.current_session_id
			}, "WORKFLOW_START")

			if not query:
				return {"error": "Missing query parameter"}

			if not data:
				return {"error": "Missing data parameter"}

			# Step 1: Analyze query
			self.log_debug("STEP_1_ANALYZE_START", {"query": query}, "STEP")
			analyze_result = await self._analyze_query({"query": query, "data": data})
			if analyze_result.get("status") != "success":
				self.log_debug("STEP_1_ANALYZE_FAILED", analyze_result, "ERROR")
				return analyze_result

			steps = analyze_result["data"]["steps"]
			self.log_debug("STEP_1_ANALYZE_COMPLETE", {"steps": steps}, "STEP")

			# Step 2: Create task graph
			self.log_debug("STEP_2_TASK_GRAPH_START", {"steps": steps}, "STEP")
			task_graph_result = await self._create_task_graph({"steps": steps, "data": data})
			if task_graph_result.get("status") != "success":
				self.log_debug("STEP_2_TASK_GRAPH_FAILED", task_graph_result, "ERROR")
				return task_graph_result

			task_graph = task_graph_result["data"]["task_graph"]
			self.log_debug("STEP_2_TASK_GRAPH_COMPLETE", {
				"task_graph": task_graph,
				"task_count": len(task_graph)
			}, "STEP")

			# Step 3: Execute task graph
			self.log_debug("STEP_3_EXECUTE_START", {"task_count": len(task_graph)}, "STEP")
			execution_result = await self._execute_task_graph({"task_graph": task_graph, "data": data})
			if execution_result.get("status") != "success":
				self.log_debug("STEP_3_EXECUTE_FAILED", execution_result, "ERROR")
				return execution_result

			final_output = execution_result["data"]["final_output"]
			execution_state = execution_result["data"]["execution_state"]
			self.log_debug("STEP_3_EXECUTE_COMPLETE", {
				"final_output": final_output,
				"execution_state": execution_state
			}, "STEP")

			# Step 4: Merge task graph (optional)
			self.log_debug("STEP_4_MERGE_START", {"task_graph": task_graph}, "STEP")
			merge_result = await self._merge_task_graph({"task_graph": task_graph, "original_query": query})
			merged_function = merge_result["data"] if merge_result.get("status") == "success" else None
			self.log_debug("STEP_4_MERGE_COMPLETE", {"merged_function": merged_function}, "STEP")

			# Save to pending storage
			tool_graph_id = str(uuid.uuid4())

			tool_graph_entry = {
				"id": tool_graph_id,
				"query": query,
				"task_graph": task_graph,
				"merged_function": merged_function,
				"created_at": str(uuid.uuid4())  # Simple timestamp placeholder
			}
			self.pending_tools[tool_graph_id] = tool_graph_entry

			self.log_debug("STORAGE_SAVE", {
				"tool_graph_id": tool_graph_id,
				"storage_location": "self.pending_tools (in-memory)",
				"tool_graph_entry": tool_graph_entry
			}, "STORAGE")

			# Write final tool to separate files for inspection
			tool_filename = f"generated_tool_{self.current_session_id}_{tool_graph_id[:8]}.json"
			function_filename = f"generated_function_{self.current_session_id}_{tool_graph_id[:8]}.py"

			try:
				# Write complete tool graph to JSON file
				with open(tool_filename, "w", encoding="utf-8") as f:
					json.dump(tool_graph_entry, f, indent=2, ensure_ascii=False)

				# Write merged function to Python file (if exists)
				if merged_function and merged_function.strip():
					with open(function_filename, "w", encoding="utf-8") as f:
						f.write(f"# Generated Tool Function\n")
						f.write(f"# Session: {self.current_session_id}\n")
						f.write(f"# Tool ID: {tool_graph_id}\n")
						f.write(f"# Query: {query}\n")
						f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n\n")
						f.write(merged_function)

				self.log_debug("FILE_OUTPUT", {
					"tool_json_file": tool_filename,
					"function_py_file": function_filename if merged_function else "None (no merged function)",
					"files_created": [tool_filename] + ([function_filename] if merged_function else [])
				}, "FILE_CREATED")

			except Exception as e:
				self.log_debug("FILE_OUTPUT_ERROR", {
					"error": str(e),
					"tool_filename": tool_filename,
					"function_filename": function_filename
				}, "ERROR")

			final_result = {
				"status": "success",
				"data": {
					"success": True,
					"result": final_output,
					"tool_graph_id": tool_graph_id,
					"files_created": {
						"tool_graph": tool_filename,
						"merged_function": function_filename if merged_function else None
					},
					"execution_details": {
						"steps": steps,
						"task_graph": task_graph,
						"merged_function": merged_function
					}
				}
			}

			self.log_debug("GENERATE_AND_EXECUTE_COMPLETE", final_result, "WORKFLOW_COMPLETE")
			return final_result

		except Exception as e:
			error_result = {
				"status": "error",
				"message": f"Error in generate and execute: {str(e)}"
			}
			self.log_debug("GENERATE_AND_EXECUTE_ERROR", error_result, "ERROR")
			logger.error(f"Error in generate and execute: {str(e)}")
			return error_result

	async def _get_pending_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""List all tools awaiting approval"""
		try:
			return {
				"status": "success",
				"data": {
					"success": True,
					"pending_tools": list(self.pending_tools.values())
				}
			}

		except Exception as e:
			logger.error(f"Error getting pending tools: {str(e)}")
			return {
				"status": "error",
				"message": f"Error getting pending tools: {str(e)}"
			}

	async def _approve_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Approve a pending tool for future reuse"""
		try:
			tool_id = request.get("tool_id", "")

			if not tool_id:
				return {"error": "Missing tool_id parameter"}

			# Move tool from pending to approved storage
			if tool_id in self.pending_tools:
				self.approved_tools[tool_id] = self.pending_tools.pop(tool_id)
				return {
					"status": "success",
					"data": {
						"success": True,
						"message": f"Tool {tool_id} approved successfully"
					}
				}
			else:
				return {"error": "Tool not found in pending storage"}

		except Exception as e:
			logger.error(f"Error approving tool: {str(e)}")
			return {
				"status": "error",
				"message": f"Error approving tool: {str(e)}"
			}

	async def _reject_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Reject a pending tool"""
		try:
			tool_id = request.get("tool_id", "")

			if not tool_id:
				return {"error": "Missing tool_id parameter"}

			# Remove tool from pending storage (rejected tools are deleted)
			if tool_id in self.pending_tools:
				del self.pending_tools[tool_id]
				return {
					"status": "success",
					"data": {
						"success": True,
						"message": f"Tool {tool_id} rejected successfully"
					}
				}
			else:
				return {"error": "Tool not found in pending storage"}

		except Exception as e:
			logger.error(f"Error rejecting tool: {str(e)}")
			return {
				"status": "error",
				"message": f"Error rejecting tool: {str(e)}"
			}

	async def _get_approved_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""List all approved tools available for reuse"""
		try:
			return {
				"status": "success",
				"data": {
					"success": True,
					"approved_tools": list(self.approved_tools.values())
				}
			}

		except Exception as e:
			logger.error(f"Error getting approved tools: {str(e)}")
			return {
				"status": "error",
				"message": f"Error getting approved tools: {str(e)}"
			}

	async def shutdown(self) -> None:
		"""Clean up resources when shutting down."""
		self._initialized = False
		logger.info("ToolGeneratorAgent shutdown complete")

	def get_capabilities(self) -> List[Dict[str, Any]]:
		"""Return agent's capabilities."""
		return [
			{
				"name": "analyze_query",
				"description": "Break down a complex query into sequential steps (PROMPT 1: voyager_brain)",
				"parameters": {
					"query": "Natural language query to analyze (required)",
					"data": "JSON data sample for context (required)"
				}
			},
			{
				"name": "create_task_graph",
				"description": "Convert steps into structured task graph (PROMPT 2: samvid_voyager_plan)",
				"parameters": {
					"steps": "Raw steps text from analyze_query (required)",
					"data": "JSON data for context (required)"
				}
			},
			{
				"name": "generate_single_tool",
				"description": "Generate a single tool from a query (PROMPTS 4-7: POC → Generalize → Extract params → Metadata)",
				"parameters": {
					"query": "Single task query (required)",
					"data": "JSON data to process (required)"
				}
			},
			{
				"name": "execute_task_graph",
				"description": "Execute a task graph step by step (PROMPT 3: perceive + execute each task)",
				"parameters": {
					"task_graph": "List of tasks to execute (required)",
					"data": "JSON data to process (required)"
				}
			},
			{
				"name": "merge_task_graph",
				"description": "Merge task graph into single optimized function (PROMPT 8: merge_task_graph_into_function)",
				"parameters": {
					"task_graph": "Completed task graph (required)",
					"original_query": "Original user query (required)"
				}
			},
			{
				"name": "generate_and_execute",
				"description": "Complete end-to-end workflow: analyze → plan → generate → execute → merge",
				"parameters": {
					"query": "Natural language query describing what to do (required)",
					"data": "JSON data to process (required)"
				}
			},
			{
				"name": "get_pending_tools",
				"description": "List all tools awaiting approval",
				"parameters": {}
			},
			{
				"name": "approve_tool",
				"description": "Approve a pending tool for future reuse",
				"parameters": {
					"tool_id": "ID of the tool to approve (required)"
				}
			},
			{
				"name": "reject_tool",
				"description": "Reject a pending tool",
				"parameters": {
					"tool_id": "ID of the tool to reject (required)"
				}
			},
			{
				"name": "get_approved_tools",
				"description": "List all approved tools available for reuse",
				"parameters": {}
			}
		]

	def get_status(self) -> Dict[str, Any]:
		"""Return agent's current status."""
		return {
			"initialized": self._initialized,
			"healthy": self._initialized,
			"capabilities": self.get_capabilities()
		}