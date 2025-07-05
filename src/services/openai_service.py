"""
OpenAI Service for NLP tasks

Handles entity extraction and relationship extraction using OpenAI API.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from openai import OpenAI

from .config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE,
    validate_openai_config,
)

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API interactions"""

    def __init__(self):
        logging.info("Starting OPENAI Service")
        validate_openai_config()

        self.client = OpenAI()
        self.model = OPENAI_MODEL
        self.max_tokens = OPENAI_MAX_TOKENS
        self.temperature = OPENAI_TEMPERATURE

        logger.info(f"OpenAI client initialized with model: {self.model}")

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text using OpenAI"""
        try:
            prompt = self._build_entity_extraction_prompt(text)

            response = self._make_openai_call(prompt)

            return self._parse_entity_response(response)

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def extract_relationships(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities using OpenAI"""
        try:
            if not entities or len(entities) < 2:
                return []

            prompt = self._build_relationship_extraction_prompt(text, entities)

            response = self._make_openai_call(prompt)

            return self._parse_relationship_response(response)

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    def _build_entity_extraction_prompt(self, text: str) -> str:
        """Build prompt for entity extraction"""
        return f"""
Extract all named entities from this document. For each entity, provide:
1. Entity name (the exact text as it appears in the document)
2. Entity type (Person, Organization, Location, Date, Product, Event, Technology, Concept, etc.)
3. Context (a brief phrase or sentence where the entity appears, limited to 100 characters)
4. Confidence score (0.0 to 1.0 based on how certain you are about the entity)

Focus on identifying:
- People (individuals, roles)
- Organizations (companies, institutions, departments)
- Locations (addresses, cities, countries)
- Dates and Times
- Products and Services
- Legal Entities and Terms
- Financial Terms and Amounts
- Events
- Technologies
- Concepts and Ideas

Document text:
{text}

Respond with a JSON array of entities in this exact format:
{{
  "entities": [
	{{
	  "name": "entity name",
	  "type": "entity type",
	  "context": "brief context where entity appears",
	  "confidence": 0.95
	}}
  ]
}}

Only include each unique entity once with its most representative context.
"""

    def _build_relationship_extraction_prompt(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for relationship extraction"""
        entity_list = "\n".join(
            [f"- {entity['name']} ({entity['type']})" for entity in entities]
        )

        return f"""
Extract relationships between the following entities from the document. For each relationship, provide:
1. Source entity (from the list below)
2. Target entity (from the list below)
3. Relationship type (created, works_at, is_a, part_of, located_in, etc.)
4. Confidence score (0.0 to 1.0)

Available entities:
{entity_list}

Document text:
{text}

Respond with a JSON array of relationships in this exact format:
{{
  "relationships": [
	{{
	  "source": "source entity name",
	  "source_type": "source entity type",
	  "target": "target entity name",
	  "target_type": "target entity type",
	  "relationship": "relationship type",
	  "confidence": 0.85
	}}
  ]
}}

Only include relationships that are clearly supported by the text.
"""

    def _make_openai_call(self, prompt: str) -> str:
        """Make OpenAI API call (synchronous)"""
        try:
            logger.info(f"Making OpenAI API call with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=8000,  # Increased for comprehensive results
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            logger.info("OpenAI API call successful")
            return content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Async chat completion method for tools"""
        try:
            logger.info(f"Making async OpenAI chat completion call")

            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens
                or 8000,  # Default to 8000 for comprehensive results
            )

            logger.info("OpenAI chat completion call successful")
            return response

        except Exception as e:
            logger.error(f"OpenAI chat completion call failed: {e}")
            raise

    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse entity extraction response"""
        try:
            parsed = json.loads(response)
            entities = parsed.get("entities", [])

            # Validate entity format
            validated_entities = []
            for entity in entities:
                if all(
                    key in entity for key in ["name", "type", "context", "confidence"]
                ):
                    validated_entities.append(entity)
                else:
                    logger.warning(f"Skipping invalid entity: {entity}")

            logger.info(f"Extracted {len(validated_entities)} entities")
            return validated_entities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity response: {e}")
            return []

    def _parse_relationship_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse relationship extraction response"""
        try:
            parsed = json.loads(response)
            relationships = parsed.get("relationships", [])

            # Validate relationship format
            validated_relationships = []
            for rel in relationships:
                if all(
                    key in rel
                    for key in [
                        "source",
                        "source_type",
                        "target",
                        "target_type",
                        "relationship",
                        "confidence",
                    ]
                ):
                    validated_relationships.append(rel)
                else:
                    logger.warning(f"Skipping invalid relationship: {rel}")

            logger.info(f"Extracted {len(validated_relationships)} relationships")
            return validated_relationships

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse relationship response: {e}")
            return []
