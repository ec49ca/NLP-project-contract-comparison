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
import os
from typing import Dict, List, Any, Optional


class PromptService:
    """Service for managing simplified dynamic prompt templates"""

    def __init__(self, prompt_dir: str = "src/prompts"):
        """
        Initializes the PromptService by loading prompt templates from a directory.
        """
        self._prompt_dir = prompt_dir
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Loads all prompts from the directory structure into memory.
        Each subdirectory in the prompt_dir is considered a prompt,
        containing system.txt and user.txt files.
        """
        prompts = {}
        if not os.path.isdir(self._prompt_dir):
            return prompts

        for prompt_name in os.listdir(self._prompt_dir):
            prompt_path = os.path.join(self._prompt_dir, prompt_name)
            if os.path.isdir(prompt_path):
                system_path = os.path.join(prompt_path, "system.txt")
                user_path = os.path.join(prompt_path, "user.txt")

                system_prompt = ""
                if os.path.exists(system_path):
                    with open(system_path, "r") as f:
                        system_prompt = f.read()

                user_prompt = ""
                if os.path.exists(user_path):
                    with open(user_path, "r") as f:
                        user_prompt = f.read()

                prompts[prompt_name] = {
                    "system": system_prompt,
                    "user": user_prompt,
                }
        return prompts

    def get_prompt(self, prompt_name: str, **kwargs) -> Dict[str, str]:
        """
        Gets a prompt by name and formats it with the provided keyword arguments.
        """
        prompt_template = self._prompts.get(prompt_name)
        if not prompt_template:
            raise ValueError(f"Prompt '{prompt_name}' not found in {self._prompt_dir}.")

        system_prompt = prompt_template["system"].format(**kwargs)
        user_prompt = prompt_template["user"].format(**kwargs)

        return {"system": system_prompt.strip(), "user": user_prompt.strip()}

    def get_complexity_assessment_prompt(
        self, query: str, data_sample: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT 1: Assess query complexity and determine processing path.
        """
        return self.get_prompt(
            "complexity_assessment",
            query=query,
            data_sample=json.dumps(data_sample[:5], indent=2),
        )

    def get_direct_generation_prompt(
        self, query: str, data_sample: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT 2A: Direct code generation for simple queries.
        """
        return self.get_prompt(
            "direct_generation",
            query=query,
            data_sample=json.dumps(data_sample[:3], indent=2),
        )

    def get_analyze_and_plan_prompt(
        self, query: str, data_sample: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT 2B: Analyze complex query and create execution plan.
        """
        return self.get_prompt(
            "analyze_and_plan",
            query=query,
            data_sample=json.dumps(data_sample[:3], indent=2),
        )

    def get_complete_solution_prompt(
        self, query: str, data_sample: List[Dict[str, Any]], analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        PROMPT 3: Generate complete solution for complex queries.
        """
        return self.get_prompt(
            "complete_solution",
            query=query,
            data_sample=json.dumps(data_sample[:3], indent=2),
            analysis=json.dumps(analysis, indent=2),
        )

    def get_parameterize_and_document_prompt(
        self, query: str, function_code: str, data_sample: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT 4: Add parameters and metadata to generated function.
        """
        return self.get_prompt(
            "parameterize_and_document",
            query=query,
            function_code=function_code,
            data_sample=json.dumps(data_sample[:3], indent=2),
        )

    def get_intent_classification_prompt(self, query: str) -> Dict[str, str]:
        """
        PROMPT: Classify the user's intent for a knowledge graph query.
        """
        return self.get_prompt("intent_classification", query=query)

    def get_ner_el_prompt(
        self, entity_types_text: str, chunk: str, confidence_threshold: str
    ) -> Dict[str, str]:
        """
        PROMPT for Named Entity Recognition and Entity Linking.
        """
        return self.get_prompt(
            "ner_el",
            entity_types_text=entity_types_text,
            chunk=chunk,
            confidence_threshold=confidence_threshold,
        )

    def get_entity_extraction_prompt(
        self,
        text: str,
        entities_list: List[Dict[str, Any]],
        existing_entities: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        PROMPT for entity extraction.
        """
        entities_list = "\n".join(
            [
                f"\t- {entity['type']}: {entity['description']}"
                for entity in entities_list
            ]
        )

        existing_entities = "\n".join(
            [f"\t- {entity['type']}: {entity['text']}" for entity in existing_entities]
        )

        return self.get_prompt(
            "entity_extraction",
            text=text,
            entities_list=entities_list,
            existing_entities=existing_entities,
        )

    def get_relationship_extraction_prompt(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        PROMPT for relationship extraction.
        """

        # Format entities as a list of entity names for the template
        entities_list = "\n".join(
            [
                f"\t- {entity['text']} ({entity['type']}) - {entity['context']}"
                for entity in entities
            ]
        )

        return self.get_prompt(
            "relationship_extraction",
            text=text,
            entities=entities_list,
        )

    def get_relation_extraction_prompt(
        self, content: str, relation_types_text: str
    ) -> Dict[str, str]:
        """
        PROMPT for relation extraction.
        """
        return self.get_prompt(
            "relation_extraction",
            content=content,
            relation_types_text=relation_types_text,
        )

    def get_meta_agent_handle_agent_request_prompt(
        self, tools_str: str, query: str, data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        SYSTEM PROMPT for meta_agent to handle agent request.
        """

        return self.get_prompt(
            "meta_agent_handle_agent_request",
            tools=tools_str,
            query=query,
            data=json.dumps(data, indent=2),
        )

    def get_meta_agent_handle_no_agent_available_request_prompt(
        self, query: str, original_query: str, reasoning: str, data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        SYSTEM PROMPT for meta_agent to handle no agent available request.
        """
        return self.get_prompt(
            "meta_agent_handle_no_agent_available_request",
            query=query,
            original_query=original_query,
            reasoning=reasoning,
            data=json.dumps(data, indent=2),
        )


# Global prompt service instance
prompt_service = PromptService()
