import json
from typing import Any, Dict, List
from voyagertask_python.parse_task_graph import VoyagerTask


async def voyager_perceive(
    task_id: str,
    original_query: str,
    reasoning_prompt: str,
    task_graph: List[VoyagerTask],
    execution_state: Dict[str, Any],
    client: Any
) -> str:
    # Find task and its dependencies
    depends_on = next((t.depends_on for t in task_graph if t.id == task_id), [])
    flat_depends_on = []
    for item in depends_on:
        if isinstance(item, list):
            flat_depends_on.extend(item)
        else:
            flat_depends_on.append(item)

    # Build context from execution_state
    context_snippet: Dict[str, Any] = {}
    for dep_id in flat_depends_on:
        result = execution_state.get(dep_id)
        if isinstance(result, dict) and "output" in result:
            context_snippet[dep_id] = result["output"]
        else:
            context_snippet[dep_id] = result or "<no output>"

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
{json.dumps([t.__dict__ for t in task_graph], indent=2)}

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

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                { "role": "system", "content": system_prompt.strip() },
                { "role": "user", "content": user_prompt.strip() }
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as error:
        raise RuntimeError(f"Failed to rewrite query: {str(error)}")
