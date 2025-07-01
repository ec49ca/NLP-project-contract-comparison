import json
from datetime import datetime
from typing import Optional, Any, Dict, List

from .generator import generate_poc_code
from .generalizer import generalize_poc_code
from .kwargs import extract_runtime_kwargs
from .runner import execute_agent
from .intent_capabilities import generate_intent_capabilities_tags
from .tool_reuse import find_and_execute_existing_tool
from .types import AgentContext
from .utils import (
    get_field_value_map,
    describe_field_schema,
    generate_unique_id,
    extract_tags_from_kwargs,
    build_input_schema,
    build_example_block,
    infer_output_schema,
    generate_hash_simple
)
from .storage import save_agent, retrieve_agents


def replace_kwarg_values_with_variables(kwargs: Dict[str, Any], variable_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to replace kwarg values with actual variable outputs."""
    new_kwargs = kwargs.copy()
    for key, value in new_kwargs.items():
        if isinstance(value, str) and value in variable_outputs:
            new_kwargs[key] = variable_outputs[value]
    return new_kwargs


async def get_answer_responses(
    query: str,
    essence_data: List[Dict[str, Any]],
    verbose: bool = True,
    agent_context: Optional[AgentContext] = None,
    ideal_output_example: Optional[str] = None,
    variable_outputs: Dict[str, Any] = {},
    client: Optional[Any] = None
) -> Dict[str, Any]:
    """Main function to generate and execute a tool for a query."""
    data = essence_data
    json_context_str = json.dumps(data, indent=2)
    field_value_map = get_field_value_map(data)
    field_schema_summary = describe_field_schema(field_value_map)

    if verbose:
        print("🤖 Generating new agent...")

    # === Generate POC
    poc_result = await generate_poc_code(query, data, field_schema_summary, agent_context, ideal_output_example, client)
    poc_code = poc_result.get("code")
    poc_error = poc_result.get("error")
    if poc_error or not poc_code:
        return {"error": poc_error or "Failed to generate POC code."}

    # === Generalize to reusable function
    generalize_result = await generalize_poc_code(poc_code, data, query, agent_context, ideal_output_example, client)
    generalized_code = generalize_result.get("code")
    generalize_error = generalize_result.get("error")
    generalize_metadata = generalize_result.get("metadata", {})

    if generalize_error or not generalized_code:
        return {"error": generalize_error or "Failed to generalize code."}

    if verbose:
        print("🔍 Generalizer metadata:", generalize_metadata)

    # === Extract runtime kwargs
    matched_fields = await extract_runtime_kwargs(
        query,
        generalized_code,
        json_context_str,
        field_value_map,
        field_schema_summary,
        verbose,
        generalize_metadata.get("kwargsComment"),
        client
    )

    execution_kwargs = replace_kwarg_values_with_variables(matched_fields, variable_outputs)

    # === Generate capabilities + tags
    capability_list = ["filtering", "aggregation", "transformation"]
    tag_list = extract_tags_from_kwargs(matched_fields)

    if verbose:
        print("🎯 Generating intent and metadata...")

    metadata_result = await generate_intent_capabilities_tags(
        query,
        generalized_code,
        data,
        capability_list,
        tag_list,
        client
    )

    metadata = metadata_result.get("result", {})
    metadata_error = metadata_result.get("error")

    if metadata_error:
        print("⚠️ Failed to generate metadata:", metadata_error)
        metadata["intent_summary"] = query
        metadata["capabilities"] = ["filtering"]
        metadata["tags"] = []

    if verbose:
        print("📝 Generated intent summary:", metadata["intent_summary"])
        print("🏷️  Generated capabilities:", metadata["capabilities"])
        print("🔖 Generated tags:", metadata["tags"])

    query_hash = generate_hash_simple(query)
    agent_name = f"agent_{query_hash}"

    base_agent_data = {
        "id": generate_unique_id(query),
        "tool_id": agent_name,
        "description": query,
        "intent_summary": metadata["intent_summary"],
        "poc_code": poc_code,
        "code": generalized_code,
        "kwargs_ex": json.dumps(matched_fields, indent=2),
        "kwargs_comment": generalize_metadata.get("kwargsComment"),
        "input_schema": build_input_schema(matched_fields),
        "examples": [],
        "tags": metadata["tags"],
        "created_at": datetime.utcnow().isoformat(),
        "capabilities": metadata["capabilities"],
        "prompt_versions": {
            "poc": "v1.0",
            "generalizer": "v1.0",
            "kwargs_extractor": "v1.0"
        }
    }

    print("🔍 Base agent data:", base_agent_data)

    # === Save agent before running
    save_agent(agent_name, base_agent_data)

    # === Execute agent
    output_example = await execute_agent(agent_name, data, execution_kwargs)

    # === Save output metadata
    base_agent_data["examples"] = build_example_block(matched_fields, output_example)
    base_agent_data["output_schema"] = infer_output_schema(output_example)
    base_agent_data["last_successful_run"] = datetime.utcnow().isoformat()

    save_agent(agent_name, base_agent_data)

    return {
        "code": generalized_code,
        "kwargs": matched_fields,
        "output": output_example
    }


async def process_query(
    query: str,
    data: List[Dict[str, Any]],
    verbose: bool = True,
    use_reuse: bool = False,
    agent_context: Optional[AgentContext] = None,
    ideal_output_example: Optional[str] = None,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    """Main entry point that handles both reuse and generation."""
    if use_reuse:
        reuse_result = await find_and_execute_existing_tool(query, data, verbose)
        if reuse_result.get("result") is not None:
            return reuse_result["result"]
        if verbose:
            print("🔄 Falling back to generating new tool")
            if reuse_result.get("error"):
                print("Previous error:", reuse_result["error"])

    return await get_answer_responses(query, data, verbose, agent_context, ideal_output_example, {}, client)
