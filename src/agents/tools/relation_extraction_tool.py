import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class RelationExtractionTool:
    """Tool for extracting relationships from preprocessed content using GPT-4o"""

    def __init__(self):
        self.name = "relation_extraction"
        self.openai_service = OpenAIService()

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """
        Extract relationships from preprocessed content using GPT-4o

        Args:
            preprocessed_content: The preprocessed text content
            relation_types: List of relationship types to focus on (optional)
            confidence_threshold: Minimum confidence score (0.0-1.0)
            chunk_size: Size of text chunks for processing
            enable_logging: Whether to log the query and results
            log_file_path: Directory for log files
            log_file_name: Specific log file name (optional)

        Returns:
            Dictionary with extracted relationships and metadata
        """
        try:
            # Extract parameters
            preprocessed_content = arguments.get("preprocessed_content", "")
            relation_types = arguments.get("relation_types", [])
            confidence_threshold = arguments.get("confidence_threshold", 0.7)
            chunk_size = arguments.get("chunk_size", 2000)
            enable_logging = arguments.get("enable_logging", False)
            log_file_path = arguments.get("log_file_path", "/app/logs")
            log_file_name = arguments.get("log_file_name", "")

            # Validate inputs
            if not preprocessed_content:
                return {
                    "error": "Missing preprocessed_content parameter",
                    "success": False,
                }

            if not preprocessed_content.strip():
                return {
                    "error": "Empty preprocessed content provided",
                    "success": False,
                }

            # Generate session ID for logging
            session_id = str(uuid4())[:8]

            # Log the query if enabled
            if enable_logging:
                await self._log_query(
                    session_id,
                    preprocessed_content,
                    relation_types,
                    confidence_threshold,
                    log_file_path,
                    log_file_name,
                )

            logger.info(
                f"Starting relation extraction for {len(preprocessed_content)} characters"
            )

            # Process content in chunks
            chunks = self._split_into_chunks(preprocessed_content, chunk_size)
            logger.info(f"Split content into {len(chunks)} chunks")

            all_relationships = []
            processing_stats = {
                "total_chunks": len(chunks),
                "processed_chunks": 0,
                "total_relationships": 0,
                "high_confidence_relationships": 0,
                "processing_errors": 0,
            }

            # Process each chunk
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(
                        f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)"
                    )

                    chunk_relationships = await self._extract_relationships_from_chunk(
                        chunk, relation_types, confidence_threshold, session_id
                    )

                    all_relationships.extend(chunk_relationships)
                    processing_stats["processed_chunks"] += 1
                    processing_stats["total_relationships"] += len(chunk_relationships)

                    # Count high confidence relationships
                    high_conf = sum(
                        1
                        for rel in chunk_relationships
                        if rel.get("confidence", 0) >= 0.8
                    )
                    processing_stats["high_confidence_relationships"] += high_conf

                    logger.info(
                        f"Chunk {i+1} extracted {len(chunk_relationships)} relationships"
                    )

                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {e}")
                    processing_stats["processing_errors"] += 1
                    continue

            # Post-process relationships
            final_relationships = self._post_process_relationships(
                all_relationships, confidence_threshold
            )

            # Generate comprehensive metadata
            metadata = self._generate_metadata(
                preprocessed_content, final_relationships, processing_stats
            )

            # Prepare result
            result = {
                "relationships": final_relationships,
                "total_found": len(final_relationships),
                "processing_stats": processing_stats,
                "metadata": metadata,
                "session_id": session_id,
                "success": True,
            }

            # Log the results if enabled
            if enable_logging:
                await self._log_results(
                    session_id, result, log_file_path, log_file_name
                )

            logger.info(
                f"Relation extraction completed: {len(final_relationships)} relationships found"
            )
            return result

        except Exception as e:
            logger.error(f"Error in relation extraction: {e}")
            return {
                "error": f"Relation extraction failed: {str(e)}",
                "success": False,
            }

    def _split_into_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Split content into chunks for processing"""
        if len(content) <= chunk_size:
            return [content]

        chunks = []

        # Split by double newlines (record boundaries) when possible
        records = content.split("\n\n")

        current_chunk = ""
        for record in records:
            if len(current_chunk) + len(record) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + record
                else:
                    current_chunk = record
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = record
                else:
                    # Record is too large, split it
                    chunks.append(record[:chunk_size])
                    current_chunk = record[chunk_size:]

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def _extract_relationships_from_chunk(
        self,
        chunk: str,
        relation_types: List[str],
        confidence_threshold: float,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """Extract relationships from a single chunk using GPT-4o"""

        # Build the prompt
        prompt = self._build_relation_extraction_prompt(chunk, relation_types)

        try:
            # Call GPT-4o
            response = await self.openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
                temperature=0.1,
                max_tokens=2000,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse the JSON response
            relationships = self._parse_gpt_response(response_text, session_id)

            # Filter by confidence threshold
            filtered_relationships = [
                rel
                for rel in relationships
                if rel.get("confidence", 0) >= confidence_threshold
            ]

            return filtered_relationships

        except Exception as e:
            logger.error(f"Error in GPT-4o relation extraction: {e}")
            return []

    def _build_relation_extraction_prompt(
        self, content: str, relation_types: List[str]
    ) -> str:
        """Build the GPT-4o prompt for relation extraction"""

        relation_types_text = ""
        if relation_types:
            relation_types_text = f"Focus especially on these relationship types: {', '.join(relation_types)}"

        prompt = f"""You are an expert at extracting relationships from structured text content.

Your task is to extract ALL meaningful relationships from the provided content. The content is in a clean structured format with field-value pairs.

CONTENT TO ANALYZE:
{content}

INSTRUCTIONS:
1. Extract ALL meaningful relationships, including:
   - Explicit relationships (directly stated)
   - Implicit relationships (can be reasonably inferred)
   - Attribute relationships (entity has attribute)
   - Hierarchical relationships (reports to, part of)
   - Temporal relationships (started on, ended on)
   - Transactional relationships (bought from, sold to)
   - Spatial relationships (located at, based in)
   - Causal relationships (caused by, resulted in)

2. {relation_types_text}

3. For each relationship, provide:
   - subject: The main entity (normalize to canonical form)
   - predicate: The relationship type (use clear, consistent predicates)
   - object: The related entity/value (normalize to canonical form)
   - confidence: Float 0.0-1.0 (be realistic, not overly confident)
   - context: The surrounding text that supports this relationship
   - relationship_type: Category (attribute, hierarchical, temporal, etc.)
   - metadata: Additional context like source_field, record_number, etc.

4. Use consistent predicate naming:
   - HAS_ATTRIBUTE (for properties)
   - REPORTS_TO (for hierarchies)
   - LOCATED_AT (for locations)
   - STARTED_ON, ENDED_ON (for dates)
   - WORKS_FOR (for employment)
   - PURCHASED_FROM, SOLD_TO (for transactions)
   - MEMBER_OF (for membership)
   - OWNS (for ownership)

5. Normalize entity names consistently across relationships.

6. Be comprehensive but accurate - extract as many reasonable relationships as possible.

RESPONSE FORMAT:
Return ONLY a JSON array with this exact structure:
[
  {{
    "subject": "normalized_entity_name",
    "predicate": "RELATIONSHIP_TYPE",
    "object": "normalized_target_entity",
    "confidence": 0.85,
    "context": "supporting text from source",
    "relationship_type": "attribute|hierarchical|temporal|transactional|spatial|causal",
    "metadata": {{
      "source_field": "field_name_if_applicable",
      "record_number": "record_id_if_applicable",
      "extraction_method": "explicit|inferred"
    }}
  }}
]

Return the JSON array only, no other text."""

        return prompt

    def _parse_gpt_response(
        self, response_text: str, session_id: str
    ) -> List[Dict[str, Any]]:
        """Parse GPT-4o response and extract relationships"""
        try:
            # Clean up the response
            response_text = response_text.strip()

            # Remove any markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            relationships = json.loads(response_text)

            if not isinstance(relationships, list):
                logger.error(f"GPT response is not a list: {type(relationships)}")
                return []

            # Validate and enrich each relationship
            validated_relationships = []
            for i, rel in enumerate(relationships):
                try:
                    validated_rel = self._validate_and_enrich_relationship(
                        rel, session_id, i
                    )
                    if validated_rel:
                        validated_relationships.append(validated_rel)
                except Exception as e:
                    logger.error(f"Error validating relationship {i}: {e}")
                    continue

            return validated_relationships

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Error parsing GPT response: {e}")
            return []

    def _validate_and_enrich_relationship(
        self, rel: Dict[str, Any], session_id: str, index: int
    ) -> Optional[Dict[str, Any]]:
        """Validate and enrich a single relationship"""
        try:
            # Required fields
            if not all(key in rel for key in ["subject", "predicate", "object"]):
                logger.warning(f"Relationship {index} missing required fields")
                return None

            # Ensure string values
            subject = str(rel["subject"]).strip()
            predicate = str(rel["predicate"]).strip()
            object_val = str(rel["object"]).strip()

            if not all([subject, predicate, object_val]):
                logger.warning(f"Relationship {index} has empty values")
                return None

            # Build enriched relationship
            enriched_rel = {
                "subject": subject,
                "predicate": predicate,
                "object": object_val,
                "confidence": float(rel.get("confidence", 0.5)),
                "context": str(rel.get("context", "")).strip(),
                "relationship_type": str(
                    rel.get("relationship_type", "unknown")
                ).strip(),
                "metadata": rel.get("metadata", {}),
                "extraction_id": f"{session_id}_{index}",
                "extracted_at": datetime.now().isoformat(),
            }

            # Ensure confidence is in valid range
            enriched_rel["confidence"] = max(0.0, min(1.0, enriched_rel["confidence"]))

            # Ensure metadata is a dict
            if not isinstance(enriched_rel["metadata"], dict):
                enriched_rel["metadata"] = {}

            # Add extraction metadata
            enriched_rel["metadata"]["session_id"] = session_id
            enriched_rel["metadata"]["extraction_index"] = index

            return enriched_rel

        except Exception as e:
            logger.error(f"Error validating relationship {index}: {e}")
            return None

    def _post_process_relationships(
        self, relationships: List[Dict[str, Any]], confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Post-process relationships to remove duplicates and improve quality"""
        if not relationships:
            return []

        # Remove duplicates based on (subject, predicate, object)
        seen = set()
        unique_relationships = []

        for rel in relationships:
            key = (
                rel["subject"].lower(),
                rel["predicate"].lower(),
                rel["object"].lower(),
            )
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        # Sort by confidence (highest first)
        unique_relationships.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        logger.info(
            f"Deduplicated {len(relationships)} -> {len(unique_relationships)} relationships"
        )

        return unique_relationships

    def _generate_metadata(
        self, content: str, relationships: List[Dict[str, Any]], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata about the extraction"""

        # Relationship type distribution
        rel_types = {}
        predicate_counts = {}
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}

        for rel in relationships:
            # Count relationship types
            rel_type = rel.get("relationship_type", "unknown")
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

            # Count predicates
            predicate = rel.get("predicate", "unknown")
            predicate_counts[predicate] = predicate_counts.get(predicate, 0) + 1

            # Confidence distribution
            confidence = rel.get("confidence", 0)
            if confidence >= 0.8:
                confidence_distribution["high"] += 1
            elif confidence >= 0.6:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1

        return {
            "content_length": len(content),
            "total_relationships": len(relationships),
            "relationship_types": rel_types,
            "predicate_counts": predicate_counts,
            "confidence_distribution": confidence_distribution,
            "processing_stats": stats,
            "extraction_timestamp": datetime.now().isoformat(),
        }

    async def _log_query(
        self,
        session_id: str,
        content: str,
        relation_types: List[str],
        confidence_threshold: float,
        log_file_path: str,
        log_file_name: str,
    ):
        """Log the relation extraction query"""
        try:
            # Generate log file name if not provided
            if not log_file_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_name = f"relation_extraction_{timestamp}.log"

            # Ensure log directory exists
            os.makedirs(log_file_path, exist_ok=True)

            log_file_full_path = os.path.join(log_file_path, log_file_name)

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "event_type": "query",
                "content_length": len(content),
                "content_preview": (
                    content[:200] + "..." if len(content) > 200 else content
                ),
                "relation_types": relation_types,
                "confidence_threshold": confidence_threshold,
            }

            # Write to log file
            with open(log_file_full_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.error(f"Error logging query: {e}")

    async def _log_results(
        self,
        session_id: str,
        result: Dict[str, Any],
        log_file_path: str,
        log_file_name: str,
    ):
        """Log the relation extraction results"""
        try:
            # Generate log file name if not provided
            if not log_file_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_name = f"relation_extraction_{timestamp}.log"

            # Ensure log directory exists
            os.makedirs(log_file_path, exist_ok=True)

            log_file_full_path = os.path.join(log_file_path, log_file_name)

            # Prepare log entry (without full relationships to avoid huge logs)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "event_type": "results",
                "total_relationships": result.get("total_found", 0),
                "processing_stats": result.get("processing_stats", {}),
                "metadata": result.get("metadata", {}),
                "success": result.get("success", False),
            }

            # Add sample relationships (first 3)
            if result.get("relationships"):
                log_entry["sample_relationships"] = result["relationships"][:3]

            # Write to log file
            with open(log_file_full_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.error(f"Error logging results: {e}")
