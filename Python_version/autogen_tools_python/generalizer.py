import json
import re
from typing import Optional, Any, Dict, List

from .types import AgentContext

# System prompt - defines HOW to generalize code
SYSTEM_PROMPT = """
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

# User prompt - defines WHAT to generalize
def create_user_prompt(
    poc_code: str,
    json_context: List[Dict[str, Any]],
    query: str,
    ideal_output_example: Optional[str] = None
) -> str:
    ideal_output_section = ""
    if ideal_output_example:
        ideal_output_section = f"""Here is an example or description of the kind of output the user would like to see. Use this as a general guide for structure, fields, or style, but do not treat it as a strict template. The actual output may include multiple items or differ in details:\n{ideal_output_example}\n"""
    
    return f"""
TASK: Generalize this POC code based on the user's query.

USER QUERY:
\"{query}\"

POC CODE:
{poc_code}

DATASET CONTEXT:
{json.dumps(json_context, indent=2)}

{ideal_output_section}⚠️ Return your output ONLY as a valid Python function and the # kwargs needed comment block — no explanation, no markdown.
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

# Main generalizer
async def generalize_poc_code(
    poc_code: str,
    json_context: List[Dict[str, Any]],
    query: str,
    agent_context: Optional[AgentContext] = None,
    ideal_output_example: Optional[str] = None,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": create_system_prompt(agent_context)
        },
        {
            "role": "user",
            "content": create_user_prompt(poc_code, json_context, query, ideal_output_example)
        }
    ]

    try:
        # Use provided client or create default one
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        raw_output = response.choices[0].message.content.strip() if response.choices else ""

        # Clean code block formatting
        if raw_output.startswith("```"):
            raw_output = re.sub(r"```[a-z]*\n?", "", raw_output)
            raw_output = re.sub(r"```$", "", raw_output).strip()

        # Split by comment block
        parts = re.split(r"\n#\s*kwargs\s+needed:", raw_output)
        if len(parts) != 2:
            print("⚠️ Could not find kwargs comment block in output")
            return { "code": None, "error": "Could not find kwargs comment block" }

        function_match = re.search(r"def\s+\w+\s*\([\s\S]+", parts[0])
        if not function_match:
            return { "code": None, "error": "Could not extract valid function code" }

        code = function_match.group(0).strip()
        kwargs_comment = parts[1].strip()

        print("🔍 Extracted kwargs comment:", kwargs_comment)

        return {
            "code": code,
            "error": None,
            "metadata": {
                "kwargsComment": kwargs_comment
            }
        }

    except Exception as error:
        print("❌ OpenAI API error:", str(error))
        return {
            "code": None,
            "error": str(error) or "Unknown OpenAI error"
        }
