"""
Prompt Service - Centralized prompt templates for tool generation workflow

This service provides all the GPT-4 prompt templates used in the 8-step tool generation workflow.
Each function returns the exact prompt that was used in the original Python_version implementation.
"""

import json
from typing import Dict, List, Any, Optional

class PromptService:
    """Service for managing all prompt templates used in tool generation"""

    @staticmethod
    def get_analyze_query_prompt(query: str, essence_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        PROMPT 1: Break down complex query into sequential steps (voyager_brain)
        Analyzes a user query and breaks it down into clear, sequential steps for data analysis.
        """
        system_prompt = """
You are a backend engineer breaking down a complex data analysis query into clear, sequential steps.

## AVAILABLE CAPABILITIES
Your autogen_tools system is very capable and can handle:
- **filtering**: Filter data based on conditions (e.g., "where field_value > threshold")
- **aggregation**: Calculate summaries like averages, sums, counts, min/max
- **transformation**: Modify data structure, add computed fields, reshape data
- **complex operations**: The system can handle multi-step logic in a single function call

## WHEN TO BREAK DOWN
Think function-to-function: "Is this too much for one function to do?"

**Single Step Examples** (let autogen_tools handle it):
- "find records where field_value > average field_value" → One step (system can compute average and filter)
- "calculate average field_value" → One step
- "filter records where field_value > threshold" → One step

**Multi-Step Examples** (needs intermediate values):
- "find records where field_value > average field_value AND category = 'specific_category'" → Might need 2 steps if the logic is complex
- "calculate average field_value by category, then find categories above overall average" → Needs intermediate calculations

## FINAL OUTPUT GUIDANCE
The final output should be **data** that allows an LLM to make the final comparison or answer, not the comparison itself.

**Good final outputs:**
- "produces: filtered_records" (data for LLM to analyze)
- "produces: comparison_data" (data showing both sides of comparison)
- "produces: aggregated_results" (summary data for LLM to interpret)

**Avoid final outputs like:**
- "produces: comparison_result" (don't do the comparison in code)
- "produces: answer" (don't answer the question, provide data)

## OUTPUT FORMAT
For each step, output in this format:
Step N: This will be a [data operation/variable creation]. [Describe the operation]. (needs: [dependencies]; produces: [output])

**IMPORTANT**: Be clear about dependencies:
- For data dependencies: "needs: data from step X"
- For variable dependencies: "needs: only variable var_name from step X"
- If using original dataset: DO NOT list it as a dependency
- Multiple dependencies: separate with commas

**IMPORTANT**: Be clear about output type:
- "produces: variable_name" (for scalar values that will be used by other steps - use descriptive names like average_sales, total_count, etc.)
- "produces: filtered_data" (REQUIRED name for ANY intermediate dataset output - do NOT use custom names)
- "produces: final_comparison" (REQUIRED name for the final dataset that answers the user's question - do NOT use custom names)

❗ CRITICAL: Dataset Output Names
- For ANY dataset output that will be used by later steps → MUST use "filtered_data"
- For the FINAL dataset output that answers the query → MUST use "final_comparison"
- NEVER use custom names for dataset outputs (like filtered_entries, matching_records, etc.)
- ONLY variable outputs (scalars) can have custom descriptive names

## EXAMPLES

**Simple Query - Single Step:**
Step 1: This will be a data operation. I will find records where field_value is greater than the average field_value. (produces: final_comparison)

**Complex Query - Multiple Steps:**
Step 1: This will be a variable creation. I will calculate the average field_value from the dataset and save it as average_value. (produces: average_value)
Step 2: This will be a data operation. I will filter the original dataset to include only records where field_value is greater than the average_value variable from step 1. (needs: only variable average_value from step 1; produces: final_comparison)

**Complex Query with Intermediate Dataset:**
Step 1: This will be a data operation. I will filter out all null values from the dataset. (produces: filtered_data)
Step 2: This will be a variable creation. I will calculate the average value from the filtered dataset from step 1. (needs: data from step 1; produces: average_value)
Step 3: This will be a data operation. I will filter the original dataset to find records above the average. (needs: only variable average_value from step 2; produces: final_comparison)

Output all steps as a single string, one after another, in order. Do not return an array or any extra formatting.
"""

        user_prompt = f"""
Complex query:
\"\"\"{query}\"\"\"

Here is a sample of the JSON dataset:
{json.dumps(essence_data[:50], indent=2)}

Break this down into clear, sequential steps that a backend JavaScript engineer would follow, as described above.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_create_task_graph_prompt(raw_steps_text: str) -> Dict[str, str]:
        """
        PROMPT 2: Convert steps into structured task graph (samvid_voyager_plan)
        Takes the raw steps from analyze_query and converts them into a structured task graph.
        """
        system_prompt = "You are an expert at converting multi-step plans into structured task graphs for data analysis."

        user_prompt = f"""
You are a backend agent. Given the following multi-step plan, convert it into a strict task graph.

For each step, output:
N. (taskN) [query]
# depends_on: ... (if needed)
# output: ... (if needed)

Rules:
- query: Copy the step description as-is
- depends_on: ONLY for data/dataset dependencies (e.g., "needs: data from step X")
  * If brain says "needs: data from step X" → add depends_on: taskX
  * If brain says "needs: only variable var_name from step X" → DO NOT add depends_on
  * If brain mentions "original dataset" or doesn't specify dataset → DO NOT add depends_on
  * If no data dependencies mentioned → DO NOT add depends_on
- output: Map the brain's output to appropriate names:
  * If brain says "produces: variable_name" → output: variable_name
  * If brain says "produces: filtered_data" → output: filtered_data
  * If brain says "produces: final_comparison" → output: final_comparison
  * If no clear output → omit output line

Examples:
Step: This will be a variable creation. I will calculate the average from the data array obtained in step 1 and save it as average_value. (needs: data from step 1; produces: average_value)
Output:
2. (task2) This will be a variable creation. I will calculate the average from the data array obtained in step 1 and save it as average_value. (needs: data from step 1; produces: average_value)
# depends_on: task1
# output: average_value

Step: This will be a data operation. I will filter the original dataset to include only the entries where the value is greater than the variable calculated in step 2. (needs: only variable var_name from step 2; produces: final_comparison)
Output:
3. (task3) This will be a data operation. I will filter the original dataset to include only the entries where the value is greater than the variable calculated in step 2. (needs: only variable var_name from step 2; produces: final_comparison)
# output: final_comparison

Plan:
\"\"\"{raw_steps_text}\"\"\"
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_rewrite_task_query_prompt(
        task_id: str,
        original_query: str,
        task_graph: List[Dict[str, Any]],
        context_snippet: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        PROMPT 3: Rewrite task query based on context (voyager_perceive)
        Transforms brain-generated task descriptions into explicit backend queries for autogen tools.
        """
        system_prompt = """
You are a Voyager agent that transforms brain-generated task descriptions into explicit backend queries for autogen tools.

Your job is to:
1. Take the brain's detailed task description and convert it into a clear query for autogen_tools
2. When the brain mentions using a variable from a previous step, tell autogen_tools that the variable already exists and should be used
3. Ensure the query will work with autogen tools
4. Follow the standardized formats based on operation type

❗ CRITICAL: Standardized Query Formats:

1. Data Operations (outputs a dataset):
   Format: "Filter/Transform/Process the data to [operation] and output the resulting dataset"

2. Variable Operations (outputs a scalar value):
   Format: "Calculate/Compute [operation] and output only the numeric value"

3. Operations using existing variables from previous steps:
   Format: "The variable_name which represents a value has already been created, so make a function that [operation] using the variable_name"

✅ The transformed query must:
- Follow the standardized format based on operation type
- When using a variable from a previous step, explicitly state that the variable already exists
- Clearly state what type of output to produce
- Use proper backend phrasing
- Work with autogen tools
"""

        user_prompt = f"""
Current task:
\"\"\"{original_query}\"\"\"

Task graph (for awareness of data flow):
{json.dumps(task_graph, indent=2)}

Dependencies (data from depends_on tasks):
{json.dumps(context_snippet, indent=2)}

Transform this formal description into an explicit query that:
1. Clearly states when we're using a variable instead of its value
2. Clearly states what type of output to produce
3. Uses proper backend phrasing
4. Will work with autogen tools
5. Takes into account:
   - Data from depends_on tasks (in Dependencies section)
   - The overall task graph flow
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_generate_poc_prompt(
        query: str,
        json_context: List[Dict[str, Any]],
        field_schema_summary: Dict[str, Any],
        function_name: str,
        ideal_output_example: Optional[str] = None
    ) -> Dict[str, str]:
        """
        PROMPT 4: Generate proof-of-concept function (generate_poc_code)
        Creates an initial POC function to analyze JSON dataset and answer the user's question.
        """
        system_prompt = """
  You are a Python assistant helping a user analyze a JSON dataset and generate an initial proof-of-concept (POC) function.

Guidelines:
- Explore the full JSON structure before coding
- Never assume one key is the only match
- Handle missing keys gracefully
- Infer everything based on input, do not hardcode
- Output ONLY the function code (no explanations)
- The function must be named exactly as specified
"""

        ideal_output_section = ""
        if ideal_output_example:
            ideal_output_section = f"""Here is an example or description of the kind of output the user would like to see. Use this as a general guide for structure, fields, or style, but do not treat it as a strict template. The actual output may include multiple items or differ in details:\n{ideal_output_example}\n"""

        user_prompt = f"""
  The goal is to write a Python function that answers the user's question using the dataset structure.

  Here is the full dataset (list of dictionaries):
  {json.dumps(json_context, indent=2)}

  Here is a summary of the data schema:
  {json.dumps(field_schema_summary, indent=2)}

  User question:
  \"{query}\"

{ideal_output_section}The function must be named \"{function_name}\".

⚠️ Return ONLY the function code. No explanations. No markdown.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_generalize_function_prompt(
        poc_code: str,
        json_context: List[Dict[str, Any]],
        query: str,
        ideal_output_example: Optional[str] = None
    ) -> Dict[str, str]:
        """
        PROMPT 5: Generalize POC function to be reusable (generalize_poc_code)
        Makes POC code more flexible and reusable by extracting hardcoded values into parameters.
        """
        system_prompt = """
You are a code generalization specialist. Your task is to make POC code more flexible and reusable.

RULES:
1. Identify and extract hardcoded values
2. Replace them with configurable parameters
3. Maintain the original functionality
4. Add clear documentation
5. Follow the specified output format

IMPORTANT CONSTRAINTS:
- Keep the original function's logic intact
- Replace any hardcoded values with flexible parameters using kwargs
- Generalize last-leaf nodes tied to query if possible
- The code should remain readable and runnable
- Only introduce kwargs for values that are likely to vary across similar queries
- Use values from the dataset to create these kwargs — they should match the JSON schema

KWARGS PATTERN RULES:
- All functions MUST accept (data, kwargs) as parameters
- Access field names using kwargs['fieldVar'] syntax (e.g., item[kwargs['fieldVar']])
- All kwargs keys MUST end with 'Var' (e.g., fieldVar, nameVar)
- Never hardcode field names in the function body
- Never use default values in the function signature
- Example structure:
  def functionName(data, kwargs):
      return [item for item in data if item[kwargs['fieldVar']] is not None]

STRICT KWARGS RULES:
- All kwarg key names should always have 'Var' in them (e.g., fieldVar, thresholdVar, valueVar).
- In the function code, ALWAYS use the exact kwarg key name as provided in kwargs with dictionary syntax.
- NEVER use a base name (e.g., threshold, value) without the 'Var' suffix in the function code.
- Do not rename or alias kwarg keys in the function code.
- Use kwargs['keyName'] syntax, NOT kwargs.keyName syntax.

OUTPUT FORMAT:
1. The generalized function following the data/kwargs pattern
2. A "# kwargs needed:" comment block with parameter documentation
"""

        ideal_output_section = ""
        if ideal_output_example:
            ideal_output_section = f"""Here is an example or description of the kind of output the user would like to see. Use this as a general guide for structure, fields, or style, but do not treat it as a strict template. The actual output may include multiple items or differ in details:\n{ideal_output_example}\n"""

        user_prompt = f"""
TASK: Generalize this POC code based on the user's query.

USER QUERY:
\"{query}\"

POC CODE:
{poc_code}

DATASET CONTEXT:
{json.dumps(json_context, indent=2)}

{ideal_output_section}⚠️ Return your output ONLY as a valid Python function and the # kwargs needed comment block — no explanation, no markdown.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_extract_parameters_prompt(
        query: str,
        function_code: str,
        full_json_string: str,
        field_value_map: Dict[str, Any],
        field_schema_summary: Dict[str, Any],
        kwargs_comment: Optional[str] = None
    ) -> str:
        """
        PROMPT 6: Extract runtime parameters from function (extract_runtime_kwargs)
        Determines the actual parameter values needed to run the generalized function.
        """
        kwargs_structure_section = ""
        if kwargs_comment:
            kwargs_structure_section = f"""Expected kwargs structure:
{kwargs_comment}

"""

        prompt = f"""
You are a Python assistant.

You are helping an LLM pipeline determine runtime parameters for an agent function.

User question:
\"{query}\"

Function to be used:
{function_code}

{kwargs_structure_section}Full dataset (list of records):
{full_json_string}

Field names and observed values:
{json.dumps(field_value_map, indent=2)}

Schema summary:
{json.dumps(field_schema_summary, indent=2)}

Task:
- Extract ALL keyword arguments (kwargs) needed to run the function, even if they match default values
- If the user prompt specifies a value (e.g., discount > 0.5), return that value
- If the user refers to a variable instead (e.g., "use thresholdVar instead of 0.5"), return the variable name as the kwargs value (e.g., "thresholdVar": "thresholdvalue")
- If the prompt implies using a variable name (e.g., "percentLimit"), you MUST:
  - Set the kwargs value to be the variable name: "percentLimitVar": "percentLimit"
  - The function will handle any default values internally
- Add 'Var' as a suffix to all kwargs keys (e.g., "region" → "regionVar")
- Use only values and variable names found in the prompt or dataset
- Return a single valid JSON object — no markdown, no extra explanation
- If no kwargs are needed, return: {{}}
- If the dataset is a list of primitives, also return: {{}}

⚠️ Return ONLY a JSON object. No explanations or formatting.
"""

        return prompt.strip()

    @staticmethod
    def get_generate_metadata_prompt(
        query: str,
        function_code: str,
        capability_list: List[str],
        tag_list: List[str]
    ) -> str:
        """
        PROMPT 7: Generate metadata for function (generate_intent_capabilities_tags)
        Generates intent summary, capabilities, and tags for the generated function.
        """
        prompt = f"""
You are an AI assistant that analyzes code and generates metadata.

User Query: "{query}"

Function Code:
{function_code}

Available Capabilities: {capability_list}

Initial Tags: {tag_list}

Task: Analyze the function and generate:
1. A concise intent summary (what the function does)
2. Relevant capabilities from the available list
3. Additional tags that describe the function's purpose

Return ONLY a JSON object with these fields:
- intent_summary: string
- capabilities: array of strings from the available list
- tags: array of strings (can include initial tags plus new ones)

⚠️ Return ONLY the JSON object, no explanations.
"""

        return prompt.strip()

    @staticmethod
    def get_merge_tasks_prompt(task_graph: List[Dict[str, Any]], original_query: str) -> Dict[str, str]:
        """
        PROMPT 8: Merge task graph into single function (merge_task_graph_into_function)
        Combines multiple task functions into a single optimized function.
        """
        task_graph_description = "\n\n".join([
            f"Task {i + 1} ({task['id']}):\n"
            f"- Query: {task['query']}\n"
            f"- Perceived Query: {task.get('perceived_query', 'N/A')}\n"
            f"- Depends On: {task.get('depends_on')}\n"
            f"- Input: {task.get('input')}\n"
            f"- Output: {task.get('output', 'N/A')}\n"
            f"- Code: {task.get('code', 'N/A')}\n"
            f"- Kwargs: {task.get('kwargs')}\n"
            f"- Executed Output: {task.get('executedoutput')}"
            for i, task in enumerate(task_graph)
        ])

        system_prompt = (
            "You are a Python agent tasked with merging a multi-step task graph into a single reusable function.\n\n"
            "You are given:\n"
            "- A list of modular Python functions (code) from each task\n"
            "- Each function has kwargs and may depend on the output of a previous task\n"
            "- Tasks include metadata: query, depends_on, output, kwargs, and executedoutput\n\n"
            "Your job:\n"
            "Analyze the task graph and build a single combined function:\n"
            "def merged_function(data):\n    # Task logic inline\n    return final_result\n\n"
            "IMPORTANT RULES:\n"
            "- Return ONLY the Python function code\n"
            "- Function name must be 'merged_function'\n"
            "- Use 'data' as the input\n"
            "- Handle dependencies and kwargs substitution properly\n"
            "- Flatten the structure and inline logic from each task\n"
        )

        user_prompt = f"Original Query: \"{original_query}\"\n\nTask Graph:\n{task_graph_description}\n\nPlease merge this into a single Python function."

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }