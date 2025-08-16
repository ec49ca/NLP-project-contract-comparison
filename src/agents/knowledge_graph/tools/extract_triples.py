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
        confidence_threshold = arguments.get("confidence_threshold", 0.7)
        max_triples = arguments.get("max_triples", 100)
        entities_schema = arguments.get("entities_schema", [])
        relationships_schema = arguments.get("relationships_schema", [])
        chunk_size = arguments.get("chunk_size", 10000)  # Process in chunks
        fill_database = arguments.get("fill_database", True)
        document_id = arguments.get("document_id", "")

        try:
            # Step 1: Text Preprocessing
            processed_text = self._preprocess_text(text)

            logger.info(
                f"Starting triple extraction. Content length: {len(processed_text)}"
            )

            # Step 2: Split text into manageable chunks
            chunks = self._split_into_chunks(processed_text, chunk_size)

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

            # First loop: Extract all entities from all chunks
            logger.info("Starting entity extraction phase")
            for chunk_num, chunk in enumerate(chunks, 1):
                logger.info(f"Extracting entities from chunk {chunk_num}/{len(chunks)}")

                try:
                    # Extract entities from this chunk
                    chunk_entities = await self._extract_entities_from_chunk(
                        chunk, entities_schema, chunk_num, all_entities
                    )

                    # Add new entities to running list
                    all_entities.extend(chunk_entities)

                    processing_stats["total_entities"] += len(chunk_entities)

                    logger.info(
                        f"Chunk {chunk_num}: +{len(chunk_entities)} entities. Total: {len(all_entities)} entities"
                    )

                except Exception as chunk_error:
                    logger.error(
                        f"Error processing chunk {chunk_num} for entities: {chunk_error}"
                    )
                    processing_stats["processing_errors"] += 1
                    continue

            # reset internal generated id
            for i, entity in enumerate(all_entities):
                # start at 1,2,3..
                entity["internal_generated_id"] = i + 1

            # Second loop: Extract all relationships from all chunks using all entities
            logger.info("Starting relationship extraction phase")
            for chunk_num, chunk in enumerate(chunks, 1):
                logger.info(
                    f"Extracting relationships from chunk {chunk_num}/{len(chunks)}"
                )

                try:
                    # Extract relationships using all entities found in first phase
                    chunk_relationships = await self._extract_relationships_from_chunk(
                        chunk, all_entities, relationships_schema, chunk_num
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

            processing_stats["chunks_processed"] = len(chunks)
            logger.info(f"All entities: {all_entities}")
            logger.info(f"All relationships: {all_relationships}")

            # Step 4: Post-process and deduplicate
            # TODO: implement post-processing correctly for deduplication

            logger.info(
                f"Triple extraction completed. Found {len(all_entities)} unique entities, {len(all_relationships)} unique relationships"
            )

            # return early if not filling database
            if not fill_database:
                result = {
                    "entities": all_entities,
                    "relationships": all_relationships,
                    "statistics": {
                        "chunks_processed": processing_stats["chunks_processed"],
                        "total_entities": len(all_entities),
                        "total_relationships": len(all_relationships),
                        "processing_errors": processing_stats["processing_errors"],
                    },
                    "success": True,
                }
                return result

            # Now need to start putting this into database
            # reformat into easy-to-cypher-query format
            graph_entities = []
            for entity in all_entities:
                graph_entity = {
                    "label": entity["label"],
                }
                properties = {}
                properties["uuid"] = str(uuid.uuid4())
                properties["document_id"] = document_id
                for attr in entity["attributes"]:
                    properties[attr["name"]] = attr["value"]
                graph_entity["properties"] = properties
                graph_entities.append(graph_entity)

            logger.info(f"Created {len(graph_entities)} graph entities")

            graph_relationships = []
            for relationship in all_relationships:
                subject_entity = graph_entities[
                    relationship["subject_entity_internal_generated_id"] - 1
                ]
                object_entity = graph_entities[
                    relationship["object_entity_internal_generated_id"] - 1
                ]
                graph_relationship = {
                    "subject_entity_label": subject_entity["label"],
                    "subject_entity_properties": subject_entity["properties"],
                    "object_entity_label": object_entity["label"],
                    "object_entity_properties": object_entity["properties"],
                    "relationship_type": relationship["name"],
                    "properties": {
                        "confidence": relationship["confidence"],
                        "document_id": document_id,
                        "uuid": str(uuid.uuid4()),
                    },
                }
                graph_relationships.append(graph_relationship)

            # TODO: add back in when we have neo4j working
            # # create entities and relationships queries and add to neo
            # # Insert entity triples into neo
            # for entity in graph_entities:
            #     await self._graphdb_.insert_entity(
            #         entity["label"], entity["properties"]
            #     )
            # logger.info(f"Inserted {len(graph_entities)} entities into Neo4j")
            # for relationship in graph_relationships:
            #     await self._graphdb_.insert_relationship(
            #         relationship["subject_entity_label"],
            #         relationship["subject_entity_properties"],
            #         relationship["object_entity_label"],
            #         relationship["object_entity_properties"],
            #         relationship["relationship_type"],
            #         relationship["properties"],
            #     )
            # logger.info(f"Inserted {len(graph_relationships)} relationships into Neo4j")

            # create variations on triples for embedding
            # TODO: make this more robust and like natural language
            """
			original : Sunworld Inc. grants_license_to PartyX

			question : what grants license to party x?

			subject  : What grants license to PartyX?
			object   : What does Sunworld Inc. grant license to?
			predicate: What is the relationship between Sunworld Inc. and PartyX?

			original : PartyX permits_sublicensing_to PartyY
			subject  : What permits sublicensing to PartyY?
			object   : What does PartyX permit sublicensing to?
			predicate: What is the relationship between PartyX and PartyY?
			"""

            for relationship in graph_relationships:
                triple_uuid = relationship["properties"]["uuid"]
                verb_form = relationship["relationship_type"].replace("_", " ")
                subject_entity = relationship["subject_entity_properties"]["name"]
                object_entity = relationship["object_entity_properties"]["name"]

                subject_question = f"What {verb_form} {object_entity}?"
                object_question = f"What does {subject_entity} {verb_form}?"
                object_question_2 = f"{subject_entity} {verb_form} what?"
                predicate_question = f"What is the relationship between {subject_entity} and {object_entity}?"

                full_triple_text = f"{subject_entity} {verb_form} {object_entity}"

                subject_embedding = await llm_service.create_embedding(
                    subject_question, model="text-embedding-3-small"
                )
                subject_embedding_str = (
                    "[" + ",".join(map(str, subject_embedding)) + "]"
                )

                object_embedding_1 = await llm_service.create_embedding(
                    object_question, model="text-embedding-3-small"
                )
                object_embedding_str_1 = (
                    "[" + ",".join(map(str, object_embedding_1)) + "]"
                )

                object_embedding_2 = await llm_service.create_embedding(
                    object_question_2, model="text-embedding-3-small"
                )
                object_embedding_str_2 = (
                    "[" + ",".join(map(str, object_embedding_2)) + "]"
                )

                predicate_embedding = await llm_service.create_embedding(
                    predicate_question, model="text-embedding-3-small"
                )
                predicate_embedding_str = (
                    "[" + ",".join(map(str, predicate_embedding)) + "]"
                )

                try:
                    # Subject lookup insertion
                    await self._db_.insert_embedding_lookup(
                        subject_embedding_str,
                        subject_entity,
                        full_triple_text,
                        triple_uuid,
                        document_id,
                    )
                    # Object 1 lookup insertion
                    await self._db_.insert_embedding_lookup(
                        object_embedding_str_1,
                        object_entity,
                        full_triple_text,
                        triple_uuid,
                        document_id,
                    )
                    # object 2 lookup insertionj
                    await self._db_.insert_embedding_lookup(
                        object_embedding_str_2,
                        object_entity,
                        full_triple_text,
                        triple_uuid,
                        document_id,
                    )
                    # Predicate lookup insertion
                    await self._db_.insert_embedding_lookup(
                        predicate_embedding_str,
                        verb_form,
                        full_triple_text,
                        triple_uuid,
                        document_id,
                    )
                except Exception as e:
                    logger.error(f"Error inserting vector embedding lookup: {e}")
                    continue

            return {"success": True}

        except Exception as e:
            logger.error(f"Error in extract_triples: {e}")
            # Fallback to placeholder implementation
            return self._fallback_response(confidence_threshold, max_triples)

    def _preprocess_text(self, text: str) -> str:
        """Preprocess the input text without truncation (chunking handles size)"""
        # Remove extra whitespace and normalize
        processed = " ".join(text.split())

        logger.info(f"Text preprocessed. Length: {len(processed)} characters")

        return processed

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

    def _fallback_response(
        self, confidence_threshold: float, max_triples: int
    ) -> Dict[str, Any]:
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

    def _extract_entity_text(self, entity: Dict[str, Any]) -> str:
        """Extract text content from entity regardless of format"""
        # Handle different entity formats (from schema-based extraction)
        if "text" in entity:
            return entity.get("text", "").strip()
        elif "attributes" in entity:
            # Look for text in attributes
            for attr in entity.get("attributes", []):
                if attr.get("name", "").lower() in ["text", "name", "value"]:
                    return attr.get("value", "").strip()
        return ""

    def _entity_already_extracted(
        self, new_entity: Dict[str, Any], existing_entities: List[Dict[str, Any]]
    ) -> bool:
        """Check if an entity has already been extracted to avoid duplicates"""
        new_text = self._extract_entity_text(new_entity).lower().strip()
        new_label = new_entity.get("label", "")

        if not new_text:
            return True  # Skip entities without text

        for existing in existing_entities:
            existing_text = self._extract_entity_text(existing).lower().strip()
            existing_label = existing.get("label", "")

            # Consider it duplicate if text and label match
            if new_text == existing_text and new_label == existing_label:
                return True

        return False

    async def _extract_entities_from_chunk(
        self,
        chunk: str,
        entities_schema: List[str],
        chunk_num: int,
        existing_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract entities from a single chunk, avoiding entities already extracted"""
        try:
            # Build prompt using prompt_service
            prompt = prompt_service.get_entity_extraction_prompt(
                text=chunk, entities_schema=entities_schema
            )

            # Make LLM call
            response = await self._make_llm_call(prompt)

            # Parse the response
            entities = json.loads(response["choices"][0]["message"]["content"])[
                "entities"
            ]

            # Filter out entities that were already extracted
            new_entities = []
            for entity in entities:
                if not self._entity_already_extracted(entity, existing_entities):
                    # Add chunk metadata to entities
                    entity["chunk_id"] = chunk_num
                    entity["source_chunk"] = (
                        chunk[:100] + "..." if len(chunk) > 100 else chunk
                    )
                    new_entities.append(entity)

            logger.info(
                f"Extracted {len(new_entities)} new entities from chunk {chunk_num} (filtered {len(entities) - len(new_entities)} duplicates)"
            )
            return new_entities

        except Exception as e:
            logger.error(f"Error extracting entities from chunk {chunk_num}: {e}")
            return []

    async def _extract_relationships_from_chunk(
        self,
        chunk: str,
        all_entities: List[Dict[str, Any]],
        relationships_schema: List[str],
        chunk_num: int,
    ) -> List[Dict[str, Any]]:
        """Extract relationships from a single chunk using all accumulated entities"""
        try:
            if not all_entities or len(all_entities) < 2:
                return []

            # Filter entities that are relevant to this chunk (have text present in chunk)
            chunk_relevant_entities = []
            chunk_lower = chunk.lower()

            for entity in all_entities:
                # Check if entity text appears in chunk
                entity_text = self._extract_entity_text(entity).lower()

                if entity_text and entity_text in chunk_lower:
                    chunk_relevant_entities.append(entity)

            if len(chunk_relevant_entities) < 2:
                logger.info(
                    f"Not enough relevant entities in chunk {chunk_num} for relationship extraction"
                )
                return []

            # Build prompt using prompt_service
            prompt = prompt_service.get_relationship_extraction_prompt(
                text=chunk,
                entities=chunk_relevant_entities,
                relationships_schema=relationships_schema,
            )

            # Make LLM call
            response = await self._make_llm_call(prompt)

            # Parse the response
            relationships = json.loads(response["choices"][0]["message"]["content"])[
                "relationships"
            ]

            # Add chunk metadata to relationships
            for relationship in relationships:
                relationship["chunk_id"] = chunk_num
                relationship["source_chunk"] = (
                    chunk[:100] + "..." if len(chunk) > 100 else chunk
                )

            logger.info(
                f"Extracted {len(relationships)} relationships from chunk {chunk_num} using {len(chunk_relevant_entities)} relevant entities"
            )
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships from chunk {chunk_num}: {e}")
            return []

    # --------------------------- POST PROCESSING ---------------------------

    def _post_process_entities(
        self, entities: List[Dict[str, Any]], confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Post-process entities: deduplicate, merge, validate"""
        if not entities:
            return []

        # Filter by confidence threshold
        high_confidence_entities = [
            e for e in entities if e.get("confidence", 0) >= confidence_threshold
        ]

        # Group similar entities for deduplication
        deduplicated = self._deduplicate_entities(high_confidence_entities)

        # Sort by confidence (highest first)
        deduplicated.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return deduplicated

    def _deduplicate_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate entities based on text and label"""
        seen = set()
        deduplicated = []

        for entity in entities:
            # Create a key for deduplication - handle schema-based format
            entity_text = self._extract_entity_text(entity).lower()
            entity_label = entity.get("label", "")
            key = (entity_text, entity_label)

            if key not in seen and entity_text:  # Only add if we found valid text
                seen.add(key)
                deduplicated.append(entity)
            elif entity_text:  # Only check duplicates if we have valid text
                # If duplicate, keep the one with higher confidence
                existing_index = None
                for i, e in enumerate(deduplicated):
                    e_text = self._extract_entity_text(e).lower()

                    if (e_text, e.get("label", "")) == key:
                        existing_index = i
                        break

                if existing_index is not None and entity.get(
                    "confidence", 0
                ) > deduplicated[existing_index].get("confidence", 0):
                    deduplicated[existing_index] = entity

        return deduplicated

    def _post_process_relationships(
        self, relationships: List[Dict[str, Any]], confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Post-process relationships: deduplicate, validate"""
        if not relationships:
            return []

        # Filter by confidence threshold
        high_confidence_relationships = [
            r for r in relationships if r.get("confidence", 0) >= confidence_threshold
        ]

        # Group similar relationships for deduplication
        deduplicated = self._deduplicate_relationships(high_confidence_relationships)

        # Sort by confidence (highest first)
        deduplicated.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return deduplicated

    def _deduplicate_relationships(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate relationships based on subject, object, and relationship type"""
        seen = set()
        deduplicated = []

        for relationship in relationships:
            # Create a key for deduplication
            subject_id = relationship.get("subject_entity_internal_generated_id", "")
            object_id = relationship.get("object_entity_internal_generated_id", "")
            rel_name = relationship.get("name", "")
            key = (subject_id, object_id, rel_name)

            if key not in seen:
                seen.add(key)
                deduplicated.append(relationship)
            else:
                # If duplicate, keep the one with higher confidence
                existing_index = next(
                    i
                    for i, r in enumerate(deduplicated)
                    if (
                        r.get("subject_entity_internal_generated_id", ""),
                        r.get("object_entity_internal_generated_id", ""),
                        r.get("name", ""),
                    )
                    == key
                )

                if relationship.get("confidence", 0) > deduplicated[existing_index].get(
                    "confidence", 0
                ):
                    deduplicated[existing_index] = relationship

        return deduplicated
