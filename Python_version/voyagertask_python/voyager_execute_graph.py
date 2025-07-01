from typing import Any, Dict, List
from voyagertask_python.parse_task_graph import VoyagerTask
from voyagertask_python.voyager_perceive import voyager_perceive
from voyagertask_python.voyager_execute import voyager_execute
from voyagertask_python.task_graph_merger import merge_task_graph_into_function, test_merged_function


def resolve_kwargs(kwargs: Dict[str, Any], execution_state: Dict[str, Any]) -> Dict[str, Any]:
    resolved = {}
    for key, value in kwargs.items():
        if isinstance(value, str) and value in execution_state:
            resolved[key] = execution_state[value]
        else:
            resolved[key] = value
    return resolved


async def voyager_execute_graph(
    task_graph: List[VoyagerTask],
    reasoning_prompt: str,
    essence_data: list,
    api_key: str,
    client: Any,
    original_query: str
) -> Dict[str, Any]:
    execution_state: Dict[str, Any] = {}
    variable_outputs: Dict[str, Any] = {}
    output_vars: Dict[str, Any] = {}

    for i, task in enumerate(task_graph):
        task_id = task.id
        original_task_query = task.query
        depends_on = task.depends_on
        input_values: Dict[str, Any] = {}

        # -- Set current world --
        if depends_on:
            last_dep = depends_on[-1]
            current_world = execution_state.get(last_dep, essence_data)
            print(f"Task {task_id} using {'execution_state' if last_dep in execution_state else 'original dataset'} from {last_dep}")
        else:
            current_world = essence_data
            print(f"Task {task_id} using original dataset as input data")

        # -- Resolve variable inputs --
        if isinstance(task.input, list):
            for var_name in task.input:
                val = next((execution_state.get(t.id) for t in task_graph if t.output == var_name), None)
                input_values[var_name] = val or output_vars.get(var_name, None)
        elif isinstance(task.input, dict):
            for _, var_name in task.input.items():
                val = next((execution_state.get(t.id) for t in task_graph if t.output == var_name), None)
                input_values[var_name] = val or output_vars.get(var_name, None)

        # -- Replace string references with values --
        for key, value in input_values.items():
            if isinstance(value, str) and value in execution_state:
                input_values[key] = execution_state[value]

        # -- Perceive rewritten query --
        rewritten_query = await voyager_perceive(
            task_id, original_task_query, reasoning_prompt, task_graph, execution_state, client
        )

        # Save perceived query
        if isinstance(rewritten_query, str) and rewritten_query.startswith('"') and rewritten_query.endswith('"'):
            task.perceived_query = rewritten_query[1:-1]
        else:
            task.perceived_query = rewritten_query or "(No perceived query generated)"
        print("Perceived Query for task", task_id, ":", task.perceived_query)

        # -- Resolve kwargs before execution --
        symbolic_kwargs = task.kwargs or {}
        resolved_kwargs = resolve_kwargs(symbolic_kwargs, execution_state)
        print("About to execute with kwargs:", resolved_kwargs)

        # -- Execute the function --
        exec_result = await voyager_execute(
            rewritten_query, current_world, resolved_kwargs, api_key, variable_outputs
        )

        # -- Store result --
        output = exec_result.get("output") if isinstance(exec_result, dict) else exec_result
        execution_state[task_id] = output

        if task.output:
            output_vars[task.output] = output
            execution_state[task.output] = output
            variable_outputs[task.output] = output
            print(f'Set execution_state["{task.output}"] =', output)

        # -- Store metadata in task object --
        if isinstance(exec_result, dict):
            task.code = str(exec_result.get("code")) if exec_result.get("code") else None
            kwargs_value = exec_result.get("kwargs", {})
            task.kwargs = kwargs_value if isinstance(kwargs_value, dict) else {}
            task.executedoutput = exec_result.get("output")
        else:
            task.code = None
            task.kwargs = {}
            task.executedoutput = output

    # -- Merged function logic --
    merged_function = None
    try:
        print("🔄 Generating merged function from task graph...")
        # Convert VoyagerTask objects to dictionaries for the merge function
        task_graph_dicts = [
            {
                'id': task.id,
                'query': task.query,
                'depends_on': task.depends_on,
                'input': task.input,
                'output': task.output,
                'code': task.code,
                'kwargs': task.kwargs,
                'executedoutput': task.executedoutput,
                'perceived_query': task.perceived_query
            }
            for task in task_graph
        ]
        merged_result = await merge_task_graph_into_function(task_graph_dicts, original_query, client)

        if merged_result.get("code") and not merged_result.get("error"):
            print("🧪 Testing merged function with original data...")
            test_result = test_merged_function(merged_result["code"], essence_data)

            merged_output = (
                test_result["result"]
                if test_result.get("success")
                else execution_state[task_graph[-1].id]
            )

            merged_function = {
                "code": merged_result["code"],
                "metadata": merged_result.get("metadata"),
                "output": merged_output,
                "testSuccess": test_result.get("success", False),
                "testError": test_result.get("error")
            }

            if test_result.get("success"):
                print("✅ Merged function test successful, output:", merged_output)
            else:
                print("⚠️ Merged function test failed:", test_result.get("error"))
        else:
            print("⚠️ Failed to generate merged function:", merged_result.get("error"))

    except Exception as error:
        print("❌ Error generating merged function:", str(error))

    return {
        "final_output": execution_state[task_graph[-1].id],
        "execution_state": execution_state,
        "variableOutputs": variable_outputs,
        "task_graph": task_graph,
        "mergedFunction": merged_function
    }
