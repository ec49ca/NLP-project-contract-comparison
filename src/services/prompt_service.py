"""
Simplified Dynamic Prompt Service - Efficient Tool Generation Workflow

This service provides a streamlined prompt system that dynamically routes queries
based on complexity, eliminating the overcalling problem of the original 8-step workflow.

New Flow:
1. Complexity Assessment (1 call)
2A. Simple Path: Direct Generation (1 call total)
2B. Complex Path: Analyze & Plan → Complete Solution (2-3 calls total)

Max calls: 3 (vs 27 in original system)
"""

import json
from typing import Dict, List, Any, Optional

class PromptService:
    """Service for managing simplified dynamic prompt templates"""

    @staticmethod
    def get_complexity_assessment_prompt(query: str, data_sample: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        PROMPT 1: Assess query complexity and determine processing path
        Routes queries to either simple direct generation or complex analysis path.
        """
        system_prompt = """
You are a query complexity classifier for data analysis tasks.

Your job is to determine if a query is SIMPLE or COMPLEX based on these criteria:

## SIMPLE QUERIES (Direct generation path):
- Single operation or calculation
- No interdependent steps
- No intermediate variables needed
- Can be solved with one cohesive function

Examples:
- "Find all customers with orders > $100"
- "Calculate average order value"
- "Filter products by category"
- "Group sales by region"
- "Find top 10 customers by spending"

## COMPLEX QUERIES (Analysis & planning path):
- Multiple dependent operations
- Requires intermediate calculations
- Needs step-by-step breakdown for clarity
- Benefits from understanding dependencies

Examples:
- "Find customers above average order value and compare to overall average"
- "Calculate category averages, then find products above their category average"
- "Analyze customer segments and compare performance across segments"
- "Find outliers based on multiple criteria and show their impact"

## OUTPUT FORMAT:
Return JSON with:
{
  "complexity": "SIMPLE" or "COMPLEX",
  "reasoning": "Brief explanation of why this query is simple or complex",
  "operations": ["list", "of", "main", "operations", "needed"],
  "dependencies": "Description of any interdependencies"
}

Be decisive - err on the side of SIMPLE when uncertain.
"""

        user_prompt = f"""
Analyze this query:
"{query}"

Data sample:
{json.dumps(data_sample[:5], indent=2)}

Classify the complexity and provide reasoning.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_direct_generation_prompt(query: str, data_sample: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        PROMPT 2A: Direct code generation for simple queries
        Generates complete solution in one step for straightforward queries.
        """
        system_prompt = """
You are a Python code generator for data analysis tasks.

Generate a complete, production-ready function that:
1. Takes (data, kwargs) as parameters
2. Processes the data according to the query
3. Returns the appropriate result
4. Handles edge cases gracefully
5. Uses descriptive variable names
6. Includes basic error handling

## FUNCTION STRUCTURE:
```python
def generated_function(data, kwargs):
    # Clear, efficient implementation
    # Handle edge cases
    # Return appropriate result
    return result

# KWARGS NEEDED:
# - paramName: description of parameter
# - fieldName: description of field reference
```

## REQUIREMENTS:
- Function name must be 'generated_function'
- Use kwargs for any configurable values
- All kwargs keys should end with 'Var' (e.g., thresholdVar, fieldVar)
- Access data using kwargs['fieldVar'] pattern
- Return data that answers the query
- No hardcoded values in function body
- Include kwargs documentation comment

## ERROR HANDLING:
- Check for empty data
- Handle missing fields gracefully
- Return appropriate defaults for edge cases
"""

        user_prompt = f"""
Query: "{query}"

Data structure:
{json.dumps(data_sample[:3], indent=2)}

Generate a complete function that processes this data according to the query.
Include the kwargs documentation comment.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_analyze_and_plan_prompt(query: str, data_sample: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        PROMPT 2B: Analyze complex query and create execution plan
        Breaks down complex queries for understanding while planning holistic execution.
        """
        system_prompt = """
You are a data analysis architect breaking down complex queries for implementation.

Your goal is to understand the query deeply and create a clear execution plan that will be used to generate a single holistic function.

## ANALYSIS APPROACH:
1. Break down the query into logical components
2. Identify key operations and their relationships
3. Plan data flow and intermediate calculations
4. Consider edge cases and error handling
5. Design the overall solution architecture

## OUTPUT FORMAT:
Return JSON with:
{
  "understanding": "Clear explanation of what the query asks for",
  "components": [
    {
      "operation": "Description of operation",
      "purpose": "Why this operation is needed",
      "input": "What data this operation works with",
      "output": "What this operation produces"
    }
  ],
  "data_flow": "Description of how data flows through the operations",
  "edge_cases": ["List of potential edge cases to handle"],
  "solution_approach": "High-level strategy for implementing this as a single function"
}

Focus on understanding rather than implementation details.
"""

        user_prompt = f"""
Complex query: "{query}"

Data structure:
{json.dumps(data_sample[:3], indent=2)}

Analyze this query and create a comprehensive execution plan.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_complete_solution_prompt(
        query: str,
        data_sample: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        PROMPT 3: Generate complete solution for complex queries
        Uses analysis to generate a holistic function that handles all complexity.
        """
        system_prompt = """
You are a Python expert generating production-ready data analysis functions.

Using the provided analysis, generate a complete function that handles all aspects of the complex query in a single, cohesive implementation.

## FUNCTION REQUIREMENTS:
- Function name must be 'generated_function'
- Takes (data, kwargs) as parameters
- Implements all operations from the analysis
- Handles data flow and dependencies internally
- Manages edge cases appropriately
- Returns final result that answers the query

## IMPLEMENTATION STRATEGY:
- Use the analysis to understand the full scope
- Implement all operations in logical sequence
- Handle intermediate calculations internally
- Use descriptive variable names
- Include appropriate error handling
- Optimize for readability and efficiency

## KWARGS PATTERN:
- Extract configurable values to kwargs
- All kwargs keys end with 'Var'
- Use kwargs['fieldVar'] pattern for field access
- No hardcoded values in function body

## OUTPUT FORMAT:
```python
def generated_function(data, kwargs):
    # Implementation based on analysis
    # All operations handled internally
    # Clear variable names and logic flow
    return final_result

# KWARGS NEEDED:
# - paramName: description
```

Return ONLY the function code and kwargs documentation.
"""

        user_prompt = f"""
Query: "{query}"

Data structure:
{json.dumps(data_sample[:3], indent=2)}

Analysis:
{json.dumps(analysis, indent=2)}

Generate a complete function that implements this complex query using the analysis.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }

    @staticmethod
    def get_parameterize_and_document_prompt(
        query: str,
        function_code: str,
        data_sample: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT 4: Add parameters and metadata to generated function
        Extracts runtime parameters and generates metadata for the function.
        """
        system_prompt = """
You are a code documentation specialist.

Given a function and its context, determine:
1. The runtime parameters (kwargs) needed
2. Metadata about the function's purpose and capabilities

## KWARGS EXTRACTION:
- Identify all configurable values
- Create kwargs for field references and thresholds
- Use 'Var' suffix for all kwargs keys
- Provide clear descriptions

## METADATA GENERATION:
- Intent summary: What the function does
- Capabilities: Data operations performed
- Tags: Descriptive labels for the function

## OUTPUT FORMAT:
Return JSON with:
{
  "kwargs": {
    "paramNameVar": "description of parameter"
  },
  "metadata": {
    "intent_summary": "Clear description of function purpose",
    "capabilities": ["filtering", "aggregation", "transformation"],
    "tags": ["descriptive", "tags"]
  }
}
"""

        user_prompt = f"""
Query: "{query}"

Function code:
{function_code}

Data structure:
{json.dumps(data_sample[:3], indent=2)}

Extract kwargs and generate metadata for this function.
"""

        return {
            "system": system_prompt.strip(),
            "user": user_prompt.strip()
        }