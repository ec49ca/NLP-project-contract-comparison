# voyager task root package

from .voyager_brain import voyager_brain
from .samvid_voyager_plan import samvid_voyager_plan
from .voyager_execute_graph import voyager_execute_graph
from .parse_task_graph import parse_task_graph, VoyagerTask
from .pending_tool_graph_storage import save_pending_tool_graph, get_pending_tool_graph, get_all_pending_tool_graphs, remove_pending_tool_graph
from .Storage.index import approve_tool_graph, reject_tool_graph
import uuid

async def run_voyager_task(query: str, essence_data: list, client, api_key: str, save_to_pending: bool = True):
    """
    Main function that runs the complete voyager task pipeline.
    This matches the voyagertask_final structure.
    
    Args:
        query: The user's query
        essence_data: The data to analyze
        client: OpenAI client
        api_key: OpenAI API key
        save_to_pending: Whether to save the tool graph to pending storage
    
    Returns:
        Dict with final output and execution details
    """
    # Step 1: Brain - break down query into steps
    brain_result = await voyager_brain(query, essence_data, client)
    
    # Step 2: Plan - convert steps into task graph
    plan_result = await samvid_voyager_plan(query, essence_data, client)
    
    # Step 3: Execute - run the task graph
    execution_result = await voyager_execute_graph(
        task_graph=plan_result["task_graph"],
        reasoning_prompt=plan_result["reasoning_prompt"],
        essence_data=essence_data,
        api_key=api_key,
        client=client,
        original_query=query
    )
    
    # Step 4: Save to pending storage if requested
    if save_to_pending:
        tool_graph_id = str(uuid.uuid4())
        
        # Convert VoyagerTask objects to dictionaries for JSON serialization
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
            for task in plan_result["task_graph"]
        ]
        
        tool_graph_entry = {
            "id": tool_graph_id,
            "query": query,
            "task_graph": task_graph_dicts,
            "mergedFunction": execution_result.get("mergedFunction")
        }
        save_pending_tool_graph(tool_graph_entry)
        execution_result["tool_graph_id"] = tool_graph_id
    
    return execution_result

# Also export individual functions for step-by-step usage
__all__ = [
    'run_voyager_task',
    'voyager_brain', 
    'samvid_voyager_plan',
    'voyager_execute_graph',
    'parse_task_graph',
    'VoyagerTask',
    'save_pending_tool_graph',
    'get_pending_tool_graph',
    'get_all_pending_tool_graphs',
    'remove_pending_tool_graph',
    'approve_tool_graph',
    'reject_tool_graph'
]
