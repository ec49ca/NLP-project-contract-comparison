import json
from typing import Any, Dict


async def voyager_brain(
    query: str,
    essence_data: list[dict],
    client: Any
) -> Dict[str, str]:
    system_prompt = """
You are a backend engineer breaking down a complex data analysis query into clear, sequential steps.

## AVAILABLE CAPABILITIES
Your autogen_tools system is very capable and can handle:
- **filtering**: Filter data based on conditions (e.g., "where field_value > threshold")
- **aggregation**: Calculate summaries like averages, sums, counts, min/max
- **transformation**: Modify data structure, add computed fields, reshape data
- **complex operations**: The system can handle multi-step logic in a single function call

## WHEN TO BREAK DOWN
Think function-to-function: "Is this too much for one function to do?"

**Single Step Examples** (let autogen_tools handle it):
- "find records where field_value > average field_value" → One step (system can compute average and filter)
- "calculate average field_value" → One step
- "filter records where field_value > threshold" → One step

**Multi-Step Examples** (needs intermediate values):
- "find records where field_value > average field_value AND category = 'specific_category'" → Might need 2 steps if the logic is complex
- "calculate average field_value by category, then find categories above overall average" → Needs intermediate calculations

## FINAL OUTPUT GUIDANCE
The final output should be **data** that allows an LLM to make the final comparison or answer, not the comparison itself.

**Good final outputs:**
- "produces: filtered_records" (data for LLM to analyze)
- "produces: comparison_data" (data showing both sides of comparison)
- "produces: aggregated_results" (summary data for LLM to interpret)

**Avoid final outputs like:**
- "produces: comparison_result" (don't do the comparison in code)
- "produces: answer" (don't answer the question, provide data)

## OUTPUT FORMAT
For each step, output in this format:
Step N: This will be a [data operation/variable creation]. [Describe the operation]. (needs: [dependencies]; produces: [output])

**IMPORTANT**: Be clear about dependencies:
- For data dependencies: "needs: data from step X"
- For variable dependencies: "needs: only variable var_name from step X"
- If using original dataset: DO NOT list it as a dependency
- Multiple dependencies: separate with commas

**IMPORTANT**: Be clear about output type:
- "produces: variable_name" (for scalar values that will be used by other steps - use descriptive names like average_sales, total_count, etc.)
- "produces: filtered_data" (REQUIRED name for ANY intermediate dataset output - do NOT use custom names)
- "produces: final_comparison" (REQUIRED name for the final dataset that answers the user's question - do NOT use custom names)

❗ CRITICAL: Dataset Output Names
- For ANY dataset output that will be used by later steps → MUST use "filtered_data"
- For the FINAL dataset output that answers the query → MUST use "final_comparison"
- NEVER use custom names for dataset outputs (like filtered_entries, matching_records, etc.)
- ONLY variable outputs (scalars) can have custom descriptive names

## EXAMPLES

**Simple Query - Single Step:**
Step 1: This will be a data operation. I will find records where field_value is greater than the average field_value. (produces: final_comparison)

**Complex Query - Multiple Steps:**
Step 1: This will be a variable creation. I will calculate the average field_value from the dataset and save it as average_value. (produces: average_value)
Step 2: This will be a data operation. I will filter the original dataset to include only records where field_value is greater than the average_value variable from step 1. (needs: only variable average_value from step 1; produces: final_comparison)

**Complex Query with Intermediate Dataset:**
Step 1: This will be a data operation. I will filter out all null values from the dataset. (produces: filtered_data)
Step 2: This will be a variable creation. I will calculate the average value from the filtered dataset from step 1. (needs: data from step 1; produces: average_value)
Step 3: This will be a data operation. I will filter the original dataset to find records above the average. (needs: only variable average_value from step 2; produces: final_comparison)

Output all steps as a single string, one after another, in order. Do not return an array or any extra formatting.
"""

    user_prompt = f"""
Complex query:
\"\"\"{query}\"\"\"

Here is a sample of the JSON dataset:
{json.dumps(essence_data[:50], indent=2)}

Break this down into clear, sequential steps that a backend JavaScript engineer would follow, as described above.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                { "role": "system", "content": system_prompt.strip() },
                { "role": "user", "content": user_prompt.strip() }
            ],
            temperature=0.2
        )

        raw_steps_text = response.choices[0].message.content.strip()
        return { "raw_steps_text": raw_steps_text }

    except Exception as error:
        raise RuntimeError(f"Failed to generate brain steps: {str(error)}")
