from typing import Any, Dict, Optional, Union
from autogen_tools_python.interface import get_answer_responses


ExecutionResult = Dict[str, Union[Any, str, Dict[str, Any]]]


async def voyager_execute(
    rewritten_query: str,
    json_world: Any,
    input_values: Dict[str, Any],
    api_key: str,
    variable_outputs: Dict[str, Any] = {}
) -> ExecutionResult:
    # If input is a list of .json filenames, reject
    if isinstance(json_world, list) and json_world and isinstance(json_world[0], str) and json_world[0].endswith(".json"):
        raise ValueError("File loading not supported in voyager_execute. Pass data directly.")

    essence_data = json_world  # Assuming it's already loaded

    try:
        output = await get_answer_responses(
            rewritten_query,
            essence_data,
            verbose=True,
            agent_context=None,
            ideal_output_example=None,
            variable_outputs=variable_outputs
        )

        # Handle LLM text error
        if isinstance(output, str) and output.startswith("Error"):
            return {
                "output": None,
                "error": output
            }

        # Handle object with kwargs/code/output
        if isinstance(output, dict) and ("code" in output or "kwargs" in output):
            original_kwargs = output.get("kwargs", {})
            execution_kwargs = original_kwargs.copy()

            for key, value in execution_kwargs.items():
                if isinstance(value, str) and value in input_values:
                    execution_kwargs[key] = value  # Preserve symbolic name

            return {
                "output": output.get("output", None),
                "code": output.get("code"),
                "kwargs": original_kwargs
            }

        return {
            "output": output
        }

    except Exception as e:
        return {
            "output": None,
            "error": str(e)
        }
