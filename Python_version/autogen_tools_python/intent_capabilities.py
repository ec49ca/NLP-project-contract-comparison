import json
from typing import List, Dict, Any, Optional

async def generate_intent_capabilities_tags(
    query: str,
    function_code: str,
    data: List[Dict[str, Any]],
    capability_list: List[str],
    tag_list: List[str],
    client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate intent summary, capabilities, and tags for an agent function.
    """
    try:
        prompt = f"""
You are an AI assistant that analyzes code and generates metadata.

User Query: "{query}"

Function Code:
{function_code}

Available Capabilities: {capability_list}

Initial Tags: {tag_list}

Task: Analyze the function and generate:
1. A concise intent summary (what the function does)
2. Relevant capabilities from the available list
3. Additional tags that describe the function's purpose

Return ONLY a JSON object with these fields:
- intent_summary: string
- capabilities: array of strings from the available list
- tags: array of strings (can include initial tags plus new ones)

⚠️ Return ONLY the JSON object, no explanations.
"""

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
        
        # Clean up the response
        if output.startswith("```"):
            output = output.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        result = json.loads(output)
        
        return {
            "result": result,
            "error": None
        }
        
    except Exception as error:
        return {
            "result": {
                "intent_summary": query,
                "capabilities": ["filtering"],
                "tags": tag_list
            },
            "error": str(error)
        } 