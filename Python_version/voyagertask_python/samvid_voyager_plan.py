from typing import Any, Dict, List
from voyagertask_python.parse_task_graph import parse_task_graph, VoyagerTask
from voyagertask_python.voyager_brain import voyager_brain


def build_task_metadata(task_graph: List[VoyagerTask]) -> Dict[str, Dict[str, Any]]:
    metadata: Dict[str, Dict[str, Any]] = {}
    for task in task_graph:
        metadata[task.id] = {
            "description": task.query,
            "expected_output_type": "dataset",
            "validation_criteria": [
                "Output should be a dataset or scalar",
                f"Should store output as {task.output}" if task.output else "No output specified"
            ],
            "variable_scope": {
                "inputs": list(task.input.values()) if task.input else [],
                "outputs": [task.output] if task.output else []
            }
        }
    return metadata


async def samvid_voyager_plan(
    query: str,
    essence_data: list,
    client: Any
) -> Dict[str, Any]:
    # 1. Call voyagerBrain
    brain_result = await voyager_brain(query, essence_data, client)
    raw_steps_text = brain_result["raw_steps_text"]

    # 2. Build plan prompt from steps
    plan_prompt = f"""
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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an expert at converting multi-step plans into structured task graphs for data analysis."
            },
            {
                "role": "user",
                "content": plan_prompt.strip()
            }
        ],
        temperature=0.2
    )

    raw_task_text = response.choices[0].message.content.strip()
    task_graph = parse_task_graph(raw_task_text)
    task_metadata = build_task_metadata(task_graph)

    return {
        "raw_task_text": raw_task_text,
        "reasoning_prompt": raw_steps_text,
        "task_graph": task_graph,
        "task_metadata": task_metadata
    }
