import json
import re
from typing import Optional, Any, Dict, List

from .utils import generate_hash
from .types import AgentContext

# System prompt - defines HOW to generate code
SYSTEM_PROMPT = """
  You are a Python assistant helping a user analyze a JSON dataset and generate an initial proof-of-concept (POC) function.
  
Guidelines:
- Explore the full JSON structure before coding
- Never assume one key is the only match
- Handle missing keys gracefully
- Infer everything based on input, do not hardcode
- Output ONLY the function code (no explanations)
- The function must be named exactly as specified
"""

# User prompt - defines WHAT to generate
def create_user_prompt(
    query: str,
    json_context: List[Dict[str, Any]],
    field_schema_summary: Dict[str, Any],
    function_name: str,
    ideal_output_example: Optional[str] = None
) -> str:
    ideal_output_section = ""
    if ideal_output_example:
        ideal_output_section = f"""Here is an example or description of the kind of output the user would like to see. Use this as a general guide for structure, fields, or style, but do not treat it as a strict template. The actual output may include multiple items or differ in details:\n{ideal_output_example}\n"""
    
    return f"""
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

# Create enhanced system prompt with agent context
def create_system_prompt(agent_context: Optional[AgentContext] = None) -> str:
    if not agent_context:
        return SYSTEM_PROMPT

    return (
        f"{SYSTEM_PROMPT}\n\nAGENT SPECIALIZATION:\n" +
        (f"- Domain: {agent_context.domain}\n" if agent_context.domain else "") +
        (f"- Constraints:\n  " + "\n  ".join(agent_context.constraints) + "\n" if agent_context.constraints else "") +
        (f"- Preferences:\n  " + "\n  ".join(agent_context.preferences) + "\n" if agent_context.preferences else "") +
        (f"- Knowledge: {agent_context.knowledge}\n" if agent_context.knowledge else "")
    )

# Core POC generator
async def generate_poc_code(
    query: str,
    json_context: List[Dict[str, Any]],
    field_schema_summary: Dict[str, Any],
    agent_context: Optional[AgentContext] = None,
    ideal_output_example: Optional[str] = None,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    query_hash = generate_hash(query)
    function_name = query_hash

    messages = [
        {
            "role": "system",
            "content": create_system_prompt(agent_context)
        },
        {
            "role": "user",
            "content": create_user_prompt(query, json_context, field_schema_summary, function_name, ideal_output_example)
        }
    ]

    try:
        # Use provided client or create default one
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )

        raw_output = response.choices[0].message.content.strip() if response.choices else ""

        # Clean code block formatting
        if raw_output.startswith("```"):
            raw_output = re.sub(r"```[a-z]*\n?", "", raw_output)
            raw_output = re.sub(r"```$", "", raw_output).strip()

        # Extract function definition
        function_match = re.search(r"def\s+\w+\s*\([\s\S]+?(?=\n\S|\Z)", raw_output)
        code = function_match.group(0).strip() if function_match else raw_output

        # Ensure the function has the correct name
        code = re.sub(r"def\s+\w+", f"def {function_name}", code)

        return { "code": code, "error": None }

    except Exception as error:
        print("❌ OpenAI API error:", str(error))
        return { "code": None, "error": str(error) or "Unknown OpenAI error" }
