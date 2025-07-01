from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI
import re

MergedFunctionResult = Dict[str, Any]

async def merge_task_graph_into_function(
    task_graph: List[Dict[str, Any]], original_query: str, client: Any = None
) -> MergedFunctionResult:
    try:
        # Create client if not provided
        if client is None:
            client = OpenAI()
            
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

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )

        code = response.choices[0].message.content.strip()
        code = re.sub(r"```(?:python)?\n?", "", code).strip("`")

        if "def merged_function" not in code:
            raise ValueError("LLM did not generate a valid merged function")

        return {
            "code": code,
            "metadata": {
                "originalTaskCount": len(task_graph),
                "mergedFunctionName": "merged_function",
                "dependenciesResolved": [t['id'] for t in task_graph]
            }
        }
    except Exception as e:
        return {"code": "", "error": str(e)}

def test_merged_function(function_code: str, test_data: Any) -> Dict[str, Any]:
    try:
        code = re.sub(r"```(?:python)?\n?", "", function_code).strip("`")
        namespace = {}
        exec(code, {}, namespace)
        result = namespace["merged_function"](test_data)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_merged_function(
    original_task_graph: List[Dict[str, Any]], merged_code: str
) -> Dict[str, Any]:
    task_ids = [t["id"] for t in original_task_graph]
    missing = [tid for tid in task_ids if tid not in merged_code]
    return {
        "taskCount": len(task_ids),
        "codeLength": len(merged_code),
        "hasAllTasks": len(missing) == 0,
        "missingTasks": missing
    }
