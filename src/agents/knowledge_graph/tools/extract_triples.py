"""
Extract Triples Tool

This tool extracts triples (subject-predicate-object relationships) from unstructured text using OpenAI.

Pipeline:
- extracts entities and triples from text
- generate uuids for entities and relationships
- link relationships with entity uuids (for pgvector lookup) from internal_generated_id
- convert entities into cypher query (linking to document id); executes query and inserts entities into neo
- convert triples into cypher query; executes query and inserts triples into neo
- create SOP phrases for every triple and embed them
- insert embedding-triple_uuid pairs into pgvector
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
import uuid

from _pytest.monkeypatch import K

# from src.services.neo4j_service import Neo4jService
from src.services.pgvector_service import PGVectorService
from ....services.llm_service import llm_service
from ....services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# TODO: make this not shit (should extract more entities /relationships but doesn't)


# this is the extract_triples tool. it is used to extract triples from unstructured text using OpenAI.
class ExtractTriplesTool:
    """Tool for extracting triples from unstructured text using OpenAI"""

    def __init__(self):
        self.name = "extract_triples"
        self.description = "Extract triples from unstructured text using LLM"
        self.llm_service = llm_service
        self._db_ = PGVectorService()
        # self._graphdb_ = Neo4jService()

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the extract_triples tool with chunking support"""
        text = arguments.get("text", "")
        confidence_threshold = arguments.get("confidence_threshold", 0.6)
        entities_list = arguments.get("entities_list", [])
        chunk_size = arguments.get("chunk_size", 50000)  # Process in chunks
        document_id = arguments.get("document_id", "")

        if len(entities_list) == 0:
            logger.error("No entities list provided")
            return {"success": False, "error": "No entities list provided"}

        try:
            logger.info(f"Starting triple extraction. Content length: {len(text)}")

            # Step 2: Split text into manageable chunks
            chunks = self._split_into_chunks(text, chunk_size)

            logger.info(
                f"Processing {len(chunks)} chunks for entity and relationship extraction"
            )

            # Step 3: Process chunks sequentially, maintaining running entity list
            all_entities = []
            all_relationships = []
            processing_stats = {
                "chunks_processed": 0,
                "total_entities": 0,
                "total_relationships": 0,
                "processing_errors": 0,
            }

            # todo: add context to database for triples for llm; should also say what part of contract it is from
            # First loop: Extract all entities from all chunks
            logger.info("Starting entity extraction phase")
            for chunk_num, chunk in enumerate(chunks, 1):
                logger.info(f"Extracting entities from chunk {chunk_num}/{len(chunks)}")

                try:
                    # Extract entities from this chunk
                    all_entities = await self._extract_entities_from_chunk(
                        chunk, entities_list, chunk_num, all_entities
                    )

                    logger.info(
                        f"Chunk {chunk_num}:  Total: {len(all_entities)} entities"
                    )

                except Exception as chunk_error:
                    logger.error(
                        f"Error processing chunk {chunk_num} for entities: {chunk_error}"
                    )
                    processing_stats["processing_errors"] += 1
                    continue

            logger.info(
                f"All Entities: {all_entities}",
            )
            # Second loop: Extract all relationships from all chunks using all entities
            logger.info("Starting relationship extraction phase")
            for chunk_num, chunk in enumerate(chunks, 1):
                logger.info(
                    f"Extracting relationships from chunk {chunk_num}/{len(chunks)}"
                )

                try:
                    # Extract relationships using all entities found in first phase
                    chunk_relationships = await self._extract_relationships_from_chunk(
                        chunk, all_entities, chunk_num
                    )

                    all_relationships.extend(chunk_relationships)

                    processing_stats["total_relationships"] += len(chunk_relationships)

                    logger.info(
                        f"Chunk {chunk_num}: +{len(chunk_relationships)} relationships. Total: {len(all_relationships)} relationships"
                    )

                except Exception as chunk_error:
                    logger.error(
                        f"Error processing chunk {chunk_num} for relationships: {chunk_error}"
                    )
                    processing_stats["processing_errors"] += 1
                    continue

            logger.info(f"All Relationships: {all_relationships}")

            processing_stats["chunks_processed"] = len(chunks)

            """
			original : Sunworld Inc. grants_license_to PartyX
			triple form: Sunworld Inc. grants license to PartyX
			"""

            # batch process (parallelize) this
            for relationship in all_relationships:
                full_triple_text = f"{relationship['subject']} {relationship['predicate']} {relationship['object']}"

                triple_embedding = await llm_service.create_embedding(
                    full_triple_text, model="text-embedding-3-small"
                )
                triple_embedding_str = "[" + ",".join(map(str, triple_embedding)) + "]"

                try:
                    await self._db_.insert_embedding_lookup(
                        triple_embedding_str,
                        full_triple_text,
                        document_id,
                    )
                    logger.info(
                        f"Inserted vector embedding lookup for: {full_triple_text}"
                    )

                except Exception as e:
                    logger.error(f"Error inserting vector embedding lookup: {e}")
                    continue

            return {"success": True}

        except Exception as e:
            logger.error(f"Error in extract_triples: {e}")
            # Fallback to placeholder implementation
            return self._fallback_response(confidence_threshold)

    async def _extract_relationships(
        self, text: str, entities: List[Dict[str, Any]], relationships_schema: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities using LLM service (replaces openai_service.extract_relationships)"""
        try:
            if not entities or len(entities) < 2:
                return []

            prompt = prompt_service.get_relationship_extraction_prompt(
                text=text, entities=entities, relationships_schema=relationships_schema
            )

            response = await self._make_llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    async def _make_llm_call(self, prompt: str) -> str:
        """Make LLM API call using llm_service (replaces openai_service._make_openai_call)"""
        try:
            logger.info("Making LLM API call")

            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                model="gpt-4o-mini",
                temperature=0.0,
            )

            if not response:
                raise ValueError("Empty response from LLM")

            return response
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    def _fallback_response(self) -> Dict[str, Any]:
        """Fallback response when extraction fails"""
        return {
            "error": "Failed to extract triples",
            "success": False,
        }

    # TODO: fix chunking to have overlap
    def _split_into_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Split content into manageable chunks preserving record boundaries"""
        # Split by double newlines (record boundaries) first - same as ner_el_tool
        records = content.split("\n\n")
        chunks = []
        current_chunk = ""

        for record in records:
            # If adding this record would exceed chunk size, start new chunk
            if len(current_chunk) + len(record) + 2 > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = record
            else:
                if current_chunk:
                    current_chunk += "\n\n" + record
                else:
                    current_chunk = record

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        # If no double newlines found, split by sentences
        if len(chunks) == 1 and len(chunks[0]) > chunk_size:
            # Split by single newlines
            sentences = chunks[0].split("\n")
            chunks = []
            current_chunk = ""

            for sentence in sentences:
                if (
                    len(current_chunk) + len(sentence) + 1 > chunk_size
                    and current_chunk
                ):
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    if current_chunk:
                        current_chunk += "\n" + sentence
                    else:
                        current_chunk = sentence

            if current_chunk:
                chunks.append(current_chunk.strip())

        # If still too large, force split by words
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= chunk_size:
                final_chunks.append(chunk)
            else:
                words = chunk.split()
                current_chunk = ""
                for word in words:
                    if (
                        len(current_chunk) + len(word) + 1 > chunk_size
                        and current_chunk
                    ):
                        final_chunks.append(current_chunk.strip())
                        current_chunk = word
                    else:
                        if current_chunk:
                            current_chunk += " " + word
                        else:
                            current_chunk = word

                if current_chunk:
                    final_chunks.append(current_chunk.strip())

        return final_chunks

    async def _extract_entities_from_chunk(
        self,
        chunk: str,
        entities_list: List[Dict[str, Any]],
        chunk_num: int,
        existing_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract entities from a single chunk, avoiding entities already extracted"""
        try:
            # Build prompt using prompt_service
            prompt = prompt_service.get_entity_extraction_prompt(
                text=chunk,
                entities_list=entities_list,
                existing_entities=existing_entities,
            )

            # Make LLM call
            response = await self._make_llm_call(prompt)

            # Parse the response
            entities = json.loads(response["choices"][0]["message"]["content"])[
                "entities"
            ]

            return entities

        except Exception as e:
            logger.error(f"Error extracting entities from chunk {chunk_num}: {e}")
            return []

    async def _extract_relationships_from_chunk(
        self,
        chunk: str,
        all_entities: List[Dict[str, Any]],
        chunk_num: int,
    ) -> List[Dict[str, Any]]:
        """Extract relationships from a single chunk using all accumulated entities"""
        try:
            # Build prompt using prompt_service
            prompt = prompt_service.get_relationship_extraction_prompt(
                text=chunk,
                entities=all_entities,
            )

            # Make LLM call
            response = await self._make_llm_call(prompt)

            # Parse the response
            relationships = json.loads(response["choices"][0]["message"]["content"])[
                "relationships"
            ]

            logger.info(
                f"Extracted {len(relationships)} relationships from chunk {chunk_num} using {len(all_entities)} entities"
            )
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships from chunk {chunk_num}: {e}")
            return []
