"""
NER+EL Tool - Named Entity Recognition + Entity Linking

This tool uses GPT-4 with clean preprocessed content to extract and link entities
with high accuracy. It leverages the structured format from preprocessing for
optimal results.
"""

import logging
import json
import re
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from ...services.llm_service import llm_service
from ...services.prompt_service import prompt_service

logger = logging.getLogger(__name__)


class NEREntityLinkingTool:
    """Advanced NER+EL tool using GPT-4 with structured prompts"""

    def __init__(self):
        self.name = "run_ner_el"
        self.description = "Extract and link named entities from preprocessed documents"
        self.llm_service = llm_service

        # Define entity types with clear descriptions
        self.entity_types = {
            "PERSON": "Individual people including full names, first names, last names",
            "ORGANIZATION": "Companies, institutions, government agencies, non-profits",
            "LOCATION": "Countries, cities, states, addresses, geographical locations",
            "DATE": "Dates, times, temporal expressions (2023-01-15, January 2023, etc.)",
            "ABSTRACT_TIME": "Abstract time expressions that don't refer to any particular date, but are still related to time ('week', 'year', 'month', 'a few days', etc)",
            "MONEY": "Monetary amounts, currencies, financial values ($1000, €500, etc.)",
            "PRODUCT": "Product names, service names, brand names",
            "EMAIL": "Email addresses",
            "PHONE": "Phone numbers, fax numbers",
            "ID_NUMBER": "Customer IDs, invoice numbers, reference numbers, codes",
            "PERCENTAGE": "Percentage values (50%, 0.25, etc.)",
            "QUANTITY": "Numeric quantities, measurements, amounts",
            "EVENT": "Named events, meetings, conferences, incidents",
            "DOCUMENT": "Document names, file names, report titles",
            "JOB_TITLE": "Professional titles, positions, roles",
            "SKILL": "Professional skills, competencies, technologies",
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute NER+EL on preprocessed content"""
        try:
            preprocessed_content = arguments.get("preprocessed_content", "")
            entity_types = arguments.get("entity_types", list(self.entity_types.keys()))
            confidence_threshold = arguments.get("confidence_threshold", 0.7)
            enable_linking = arguments.get("enable_linking", True)
            chunk_size = arguments.get("chunk_size", 2000)  # Process in chunks
            for_retrieval = arguments.get("for_retrieval", False)
            # TODO: add different prompt if retrieval vs extraction.

            # Logging parameters
            enable_logging = arguments.get("enable_logging", False)
            log_file_path = arguments.get("log_file_path", "/app/logs")
            log_file_name = arguments.get(
                "log_file_name",
                f"ner_el_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )

            if not preprocessed_content:
                return {
                    "error": "Missing preprocessed_content parameter",
                    "success": False,
                }

            # Validate entity types
            valid_types = [t for t in entity_types if t in self.entity_types]
            if not valid_types:
                return {
                    "error": f"No valid entity types. Supported: {list(self.entity_types.keys())}",
                    "success": False,
                }

            logger.info(
                f"Starting NER+EL processing. Content length: {len(preprocessed_content)}"
            )

            # Initialize logging if enabled
            if enable_logging:
                log_data = self._initialize_logging(
                    arguments, log_file_path, log_file_name, preprocessed_content
                )
            else:
                log_data = None

            # Process content in chunks for better accuracy
            chunks = self._split_into_chunks(preprocessed_content, chunk_size)
            all_entities = []
            processing_stats = {
                "chunks_processed": 0,
                "total_entities": 0,
                "high_confidence_entities": 0,
                "entity_type_counts": {},
                "processing_errors": 0,
            }

            # TODO: if using chunks, can parallelize
            for chunk_num, chunk in enumerate(chunks, 1):
                logger.info(f"Processing chunk {chunk_num}/{len(chunks)}")

                try:
                    # Extract entities from this chunk
                    chunk_entities = await self._extract_entities_from_chunk(
                        chunk, valid_types, confidence_threshold
                    )

                    # Perform entity linking if enabled
                    if enable_linking:
                        chunk_entities = await self._link_entities(chunk_entities)

                    all_entities.extend(chunk_entities)
                    processing_stats["chunks_processed"] += 1

                    # Update stats
                    for entity in chunk_entities:
                        entity_type = entity.get("type", "UNKNOWN")
                        processing_stats["entity_type_counts"][entity_type] = (
                            processing_stats["entity_type_counts"].get(entity_type, 0)
                            + 1
                        )

                        if entity.get("confidence", 0) >= confidence_threshold:
                            processing_stats["high_confidence_entities"] += 1

                except Exception as chunk_error:
                    logger.error(f"Error processing chunk {chunk_num}: {chunk_error}")
                    processing_stats["processing_errors"] += 1
                    continue

            # Post-process and deduplicate entities
            final_entities = self._post_process_entities(
                all_entities, confidence_threshold
            )
            processing_stats["total_entities"] = len(final_entities)

            # Generate entity relationships
            relationships = await self._extract_entity_relationships(
                final_entities, preprocessed_content
            )

            result = {
                "entities": final_entities,
                "relationships": relationships,
                "statistics": processing_stats,
                "entity_types_found": list(
                    processing_stats["entity_type_counts"].keys()
                ),
                "total_entities": len(final_entities),
                "high_confidence_entities": processing_stats[
                    "high_confidence_entities"
                ],
                "success": True,
            }

            logger.info(
                f"NER+EL completed. Found {len(final_entities)} entities, {len(relationships)} relationships"
            )

            # Log results if logging is enabled
            if enable_logging and log_data:
                self._log_results(log_data, result)

            return result

        except Exception as e:
            logger.error(f"Error in NER+EL processing: {e}")
            error_result = {"error": f"NER+EL failed: {str(e)}", "success": False}

            # Log error if logging is enabled
            if enable_logging and log_data:
                self._log_results(log_data, error_result)

            return error_result

    def _split_into_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Split content into manageable chunks preserving record boundaries"""
        # Split by double newlines (record boundaries)
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

        return chunks

    async def _extract_entities_from_chunk(
        self, chunk: str, entity_types: List[str], confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Extract entities from a single chunk using GPT-4"""

        # Create entity type descriptions for the prompt
        type_descriptions = []
        for entity_type in entity_types:
            desc = self.entity_types.get(entity_type, "")
            type_descriptions.append(f"- {entity_type}: {desc}")

        entity_types_text = "\n".join(type_descriptions)

        # Build prompt using prompt_service
        prompt_data = prompt_service.get_ner_el_prompt(
            entity_types_text, chunk, str(confidence_threshold)
        )

        try:
            # Use LLM service
            content = await self.llm_service.simple_completion(
                prompt=prompt_data["system"], response_format={"type": "json_object"}
            )

            # Parse JSON response
            try:
                result = json.loads(content)
                entities = result.get("entities", [])

                # Validate and clean entities
                validated_entities = []
                for entity in entities:
                    if self._validate_entity(entity, entity_types):
                        validated_entities.append(entity)

                return validated_entities

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT response as JSON: {e}")
                logger.error(f"Response content: {content[:500]}...")
                return []

        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return []

    def _validate_entity(self, entity: Dict[str, Any], valid_types: List[str]) -> bool:
        """Validate entity structure and content"""
        required_fields = ["text", "type", "confidence"]

        # Check required fields
        for field in required_fields:
            if field not in entity:
                return False

        # Check entity type
        if entity["type"] not in valid_types:
            return False

        # Check confidence is valid
        try:
            confidence = float(entity["confidence"])
            if not 0.0 <= confidence <= 1.0:
                return False
        except (ValueError, TypeError):
            return False

        # Check text is not empty
        if not entity["text"] or not entity["text"].strip():
            return False

        return True

    async def _link_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform entity linking to connect entities to external knowledge"""

        linked_entities = []

        for entity in entities:
            entity_copy = entity.copy()
            entity_type = entity["type"]
            entity_text = entity["text"]

            # Add entity linking based on type
            if entity_type == "PERSON":
                entity_copy["linked_info"] = await self._link_person_entity(entity_text)
            elif entity_type == "ORGANIZATION":
                entity_copy["linked_info"] = await self._link_organization_entity(
                    entity_text
                )
            elif entity_type == "LOCATION":
                entity_copy["linked_info"] = await self._link_location_entity(
                    entity_text
                )
            elif entity_type in ["DATE", "MONEY", "PERCENTAGE"]:
                entity_copy["linked_info"] = self._link_structured_entity(
                    entity_text, entity_type
                )
            else:
                entity_copy["linked_info"] = {
                    "type": "no_linking",
                    "note": "No linking available for this entity type",
                }

            linked_entities.append(entity_copy)

        return linked_entities

    async def _link_person_entity(self, person_name: str) -> Dict[str, Any]:
        """Link person entities (can be extended to external databases)"""
        # For now, provide structured parsing
        name_parts = person_name.strip().split()

        linking_info = {
            "type": "person",
            "full_name": person_name,
            "name_parts": {
                "first_name": name_parts[0] if name_parts else "",
                "last_name": name_parts[-1] if len(name_parts) > 1 else "",
                "middle_names": (
                    " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
                ),
            },
            "canonical_form": " ".join(name_parts),
            "variations": [person_name, person_name.lower(), person_name.upper()],
        }

        return linking_info

    async def _link_organization_entity(self, org_name: str) -> Dict[str, Any]:
        """Link organization entities"""
        # Basic organization parsing and normalization
        org_clean = org_name.strip()

        # Remove common suffixes for matching
        suffixes = [
            "Inc.",
            "LLC",
            "Corp.",
            "Corporation",
            "Company",
            "Co.",
            "Ltd.",
            "Limited",
        ]
        org_base = org_clean
        for suffix in suffixes:
            if org_clean.endswith(suffix):
                org_base = org_clean[: -len(suffix)].strip()
                break

        linking_info = {
            "type": "organization",
            "full_name": org_name,
            "base_name": org_base,
            "canonical_form": org_clean,
            "variations": [org_name, org_base, org_clean.lower()],
        }

        return linking_info

    async def _link_location_entity(self, location: str) -> Dict[str, Any]:
        """Link location entities"""
        # Basic location parsing
        location_clean = location.strip()

        linking_info = {
            "type": "location",
            "full_location": location,
            "canonical_form": location_clean,
            "variations": [location, location_clean.lower()],
        }

        # Try to parse address components
        if "," in location:
            parts = [part.strip() for part in location.split(",")]
            linking_info["address_components"] = parts

        return linking_info

    def _link_structured_entity(
        self, entity_text: str, entity_type: str
    ) -> Dict[str, Any]:
        """Link structured entities like dates, money, percentages"""
        linking_info = {
            "type": entity_type.lower(),
            "original_text": entity_text,
            "canonical_form": entity_text,
        }

        if entity_type == "DATE":
            # Parse and normalize dates
            normalized_date = self._normalize_date(entity_text)
            linking_info["normalized_date"] = normalized_date
            linking_info["iso_format"] = (
                normalized_date  # Could be improved with proper date parsing
            )

        elif entity_type == "MONEY":
            # Parse money amounts
            money_info = self._parse_money(entity_text)
            linking_info.update(money_info)

        elif entity_type == "PERCENTAGE":
            # Parse percentage values
            pct_info = self._parse_percentage(entity_text)
            linking_info.update(pct_info)

        return linking_info

    def _normalize_date(self, date_text: str) -> str:
        """Basic date normalization - can be improved with dateutil"""
        # Simple patterns - in production use proper date parsing library
        date_clean = date_text.strip()

        # Handle YYYY-MM-DD format
        if re.match(r"\d{4}-\d{2}-\d{2}", date_clean):
            return date_clean

        # Handle MM/DD/YYYY format
        mm_dd_yyyy = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_clean)
        if mm_dd_yyyy:
            month, day, year = mm_dd_yyyy.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        return date_clean  # Return as-is if can't parse

    def _parse_money(self, money_text: str) -> Dict[str, Any]:
        """Parse money amounts and currencies"""
        money_clean = money_text.strip()

        # Extract currency and amount
        currency_symbols = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}

        currency = "USD"  # Default
        amount_str = money_clean

        for symbol, curr in currency_symbols.items():
            if symbol in money_clean:
                currency = curr
                amount_str = money_clean.replace(symbol, "").strip()
                break

        # Extract numeric amount
        amount_match = re.search(r"[\d,]+\.?\d*", amount_str)
        if amount_match:
            amount_text = amount_match.group(0).replace(",", "")
            try:
                amount = float(amount_text)
            except ValueError:
                amount = 0.0
        else:
            amount = 0.0

        return {
            "currency": currency,
            "amount": amount,
            "amount_text": amount_str,
            "formatted": f"{currency} {amount:,.2f}",
        }

    def _parse_percentage(self, pct_text: str) -> Dict[str, Any]:
        """Parse percentage values"""
        pct_clean = pct_text.strip()

        # Extract numeric value
        pct_match = re.search(r"(\d+\.?\d*)%?", pct_clean)
        if pct_match:
            pct_value = float(pct_match.group(1))

            # Convert to decimal if it's a percentage
            if "%" in pct_clean or pct_value > 1:
                decimal_value = pct_value / 100
            else:
                decimal_value = pct_value

            return {
                "percentage": pct_value,
                "decimal": decimal_value,
                "formatted": f"{pct_value}%",
            }

        return {"percentage": 0.0, "decimal": 0.0, "formatted": "0%"}

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
        """Remove duplicate entities based on text and type"""
        seen = set()
        deduplicated = []

        for entity in entities:
            # Create a key for deduplication
            key = (entity["text"].lower().strip(), entity["type"])

            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
            else:
                # If duplicate, keep the one with higher confidence
                existing_index = next(
                    i
                    for i, e in enumerate(deduplicated)
                    if (e["text"].lower().strip(), e["type"]) == key
                )

                if entity.get("confidence", 0) > deduplicated[existing_index].get(
                    "confidence", 0
                ):
                    deduplicated[existing_index] = entity

        return deduplicated

    async def _extract_entity_relationships(
        self, entities: List[Dict[str, Any]], content: str
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        if len(entities) < 2:
            return []

        # For now, extract simple co-occurrence relationships
        # This can be enhanced with more sophisticated relationship extraction
        relationships = []

        # Group entities by record
        entities_by_record = {}
        for entity in entities:
            record_id = entity.get("record_id", "UNKNOWN")
            if record_id not in entities_by_record:
                entities_by_record[record_id] = []
            entities_by_record[record_id].append(entity)

        # Find relationships within each record
        for record_id, record_entities in entities_by_record.items():
            if len(record_entities) >= 2:
                for i, entity1 in enumerate(record_entities):
                    for entity2 in record_entities[i + 1 :]:
                        relationship = {
                            "subject": entity1["text"],
                            "subject_type": entity1["type"],
                            "object": entity2["text"],
                            "object_type": entity2["type"],
                            "relation_type": "co_occurs_in_record",
                            "context": record_id,
                            "confidence": min(
                                entity1.get("confidence", 0),
                                entity2.get("confidence", 0),
                            ),
                        }
                        relationships.append(relationship)

        return relationships

    def _initialize_logging(
        self,
        arguments: Dict[str, Any],
        log_file_path: str,
        log_file_name: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        """Initialize logging and create log entry with input data"""
        try:
            # Create log directory if it doesn't exist
            os.makedirs(log_file_path, exist_ok=True)

            # Create full log file path
            full_log_path = os.path.join(log_file_path, log_file_name)

            # Create log data structure
            log_data = {
                "log_file_path": full_log_path,
                "session_id": f"ner_el_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "start_time": datetime.now().isoformat(),
                "input_data": {
                    "content_length": len(content),
                    "content_preview": (
                        content[:500] + "..." if len(content) > 500 else content
                    ),
                    "entity_types": arguments.get("entity_types", []),
                    "confidence_threshold": arguments.get("confidence_threshold", 0.7),
                    "enable_linking": arguments.get("enable_linking", True),
                    "chunk_size": arguments.get("chunk_size", 2000),
                },
            }

            # Write initial log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "ner_el_start",
                "session_id": log_data["session_id"],
                "input_parameters": log_data["input_data"],
                "content_sample": (
                    content[:1000] + "..." if len(content) > 1000 else content
                ),
            }

            self._write_log_entry(log_data["log_file_path"], log_entry)

            logger.info(f"NER+EL logging initialized: {full_log_path}")
            return log_data

        except Exception as e:
            logger.error(f"Failed to initialize logging: {e}")
            return None

    def _log_results(self, log_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Log the results of NER+EL processing"""
        try:
            if not log_data:
                return

            # Create result log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "ner_el_complete",
                "session_id": log_data["session_id"],
                "processing_time": (
                    datetime.now() - datetime.fromisoformat(log_data["start_time"])
                ).total_seconds(),
                "success": result.get("success", False),
                "summary": {
                    "total_entities": result.get("total_entities", 0),
                    "high_confidence_entities": result.get(
                        "high_confidence_entities", 0
                    ),
                    "entity_types_found": result.get("entity_types_found", []),
                    "relationships_count": len(result.get("relationships", [])),
                    "processing_stats": result.get("statistics", {}),
                },
            }

            # Add error information if present
            if "error" in result:
                log_entry["error"] = result["error"]
                log_entry["event"] = "ner_el_error"

            # Add detailed results (truncated for readability)
            if result.get("success", False):
                log_entry["entities_sample"] = result.get("entities", [])[
                    :5
                ]  # First 5 entities
                log_entry["relationships_sample"] = result.get("relationships", [])[
                    :3
                ]  # First 3 relationships

            self._write_log_entry(log_data["log_file_path"], log_entry)

            logger.info(f"NER+EL results logged to: {log_data['log_file_path']}")

        except Exception as e:
            logger.error(f"Failed to log results: {e}")

    def _write_log_entry(self, log_file_path: str, log_entry: Dict[str, Any]) -> None:
        """Write a log entry to the log file"""
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, indent=2, ensure_ascii=False) + "\n")
                f.write("-" * 80 + "\n")  # Separator between entries
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}")
