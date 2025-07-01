import json
import re
from typing import Optional, Any, Dict, List

async def extract_runtime_kwargs(
    query: str,
    function_code: str,
    full_json_string: str,
    field_value_map: Dict[str, Any],
    field_schema_summary: Dict[str, Any],
    verbose: bool = True,
    kwargs_comment: Optional[str] = None,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    # First try to extract kwargs from the comment block
    kwargs_comment_match = re.search(r"#\s*kwargs\s+needed:\s*\{[\s\S]*?\}", function_code)
    if kwargs_comment_match:
        try:
            kwargs_str = kwargs_comment_match.group(0)
            kwargs_str_cleaned = re.sub(r"#\s*kwargs\s+needed:\s*", '', kwargs_str)
            kwargs_obj = json.loads(kwargs_str_cleaned)
            return kwargs_obj
        except Exception as e:
            print("⚠️ Could not parse kwargs comment block:", str(e))

    # If no valid kwargs comment found, fall back to GPT
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

    try:
        # Use provided client or create default one
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip()
                }
            ]
        )

        output = response.choices[0].message.content.strip() if response.choices else ""

        # Clean code block formatting
        output = re.sub(r"```(?:json)?", "", output)
        output = re.sub(r"```", "", output).strip()

        match = re.search(r"\{[\s\S]+\}", output)
        if match:
            output = match.group(0)

        if verbose:
            print("🧠 Cleaned runtime kwargs:", output)

        parsed = json.loads(output)

        # Ensure all keys have Var suffix
        result = {}
        for key, value in parsed.items():
            new_key = key if key.endswith("Var") else f"{key}Var"
            result[new_key] = value

        return result

    except Exception as e:
        print("❌ GPT kwargs inference failed:", str(e))
        return {}
