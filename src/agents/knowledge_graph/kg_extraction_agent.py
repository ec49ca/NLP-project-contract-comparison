"""
Knowledge Graph Extraction Agent - Triple Extraction Implementation
"""

# TODO: Parallelize all gpt prompts for better scatter gather.
# TODO: (experiment with this, maybe it is already correct, but don't know for sure) ner_el_tool does not need to only extract entities. it can also get relationships but because of bad prompting it only gets simple relationships. this was initially the reason i created the relation_extraction tool, but it is redundant (test this assumption as well)
# TODO: make the ner tool much cleaner and refactor it
# TODO: optimize prompts for cost and performance (more tokens is more expensive but might give better value)
# TODO: actually move everything to prompt service and create files for each prompt
# TODO: remove entity types dependence
# TODO: cross user feedback loop for entity deduplication (people within an org might call a specific product by some name or osmething else)
# TODO: tenant based entities using key lookups
# TODO: for orchestrator: alignment for enterprise chat
# TODO: create data cold start for new enterprises. need to be able to ocmpletely download all data into KG
# TODO: add global data so anything on wikipedia can be referenced
# TODO: add real time kg updates so news from around the world gets updated into kg as well
# TODO: add different prompts for retrieval vs extraction ner
# TODO: find all passwords and move to env. update for prod or dev env
# TODO: refactor entity traversal and all hybrid retrievals into a single tool and use that.
# TODO: remove get capabilities dependence in mcp_server.py, shouldn't have to write capabilities twice.
# TODO: create neo4j db migration scripts
# TODO: preprocessor needs to check for typos and clean text as well
# TODO: set up claude integration for auto tool generation.
# TODO: parallelize cypher queries
# TODO: create kg benchmarking suite
# TODO: add validation so that any return value for a tool actually returns the returnValues field
# TODO: make it not stupid to add/remove tools/agents

# ideas:
# add "from chunk" relation to lookup and add to context easily (possibly replaces quadruple necessity)
# for client specific kg entities, bake in client specific context: sunworld is fruit development context


import logging
from typing import Dict, List, Any, Optional
from ...interfaces.agent import AgentInterface
from .tools.extract_triples import ExtractTriplesTool
from .tools.detect_document_tool import DetectDocumentTool
from .tools.ner_el_tool import NEREntityLinkingTool
from .tools.preprocess_document_tool import PreprocessDocumentTool
from .tools.relation_extraction_tool import RelationExtractionTool

# from ...services.neo4j_service import Neo4jService
from ...services.pgvector_service import PGVectorService
from ...services.llm_service import llm_service
from ...services.prompt_service import prompt_service
from uuid import UUID
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeGraphExtractionAgent(AgentInterface):

    def __init__(self):
        self._agent_id_str = "knowledge_graph_extraction"
        self._uuid = None
        self.agent_id = "knowledge_graph_extraction"
        self._name = "Knowledge Graph Extraction Agent"
        self._description = "Extract triples from data and perform graph operations"
        self._initialized = False
        self.category = "knowledge_management"
        self.status = "initialized"
        self._tools = {}
        # self._graphdb_ = Neo4jService()
        self._db_ = PGVectorService()

        self._tools["extract_triples"] = ExtractTriplesTool()
        self._tools["detect_document_type"] = DetectDocumentTool()
        self._tools["preprocess_document"] = PreprocessDocumentTool()
        self._tools["run_ner_el"] = NEREntityLinkingTool()
        self._tools["run_relation_extraction"] = RelationExtractionTool()

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "retrieve",
                "description": "Retrieve information from the knowledge graph based on the user's query",
                "parameters": {
                    "query": "User query to retrieve information (required)",
                    "intent": "Intent of the user query (optional)",
                    "context": "Additional context for the query (optional)",
                },
                "returnValues": {
                    "intent": "string - Classified intent of the user query",
                    "intent_confidence": "number - Confidence score for the intent classification (0.0-1.0)",
                    "extracted_entities": "array - List of entities extracted from the query with text, type, and confidence",
                    "extracted_relationships": "array - List of relationships extracted from the query",
                    # "results": "array - Retrieved information from knowledge graph (future implementation)",
                    # "metadata": "object - Additional execution metadata (future implementation)",
                },
            },
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Agent not initialized"}

        command = request.get("command", "")

        if command == "extract_triples":
            return await self._extract_triples(request)
        elif command == "detect_document_type":
            return await self._detect_document_type(request)
        elif command == "preprocess_document":
            return await self._preprocess_document(request)
        elif command == "run_ner_el":
            return await self._run_ner_el(request)
        elif command == "run_relation_extraction":
            return await self._run_relation_extraction(request)
        elif command == "create_quadruples":
            return await self._create_quadruples(request)
        elif command == "process_file_to_ner":
            return await self._process_file_to_ner(request)
        # elif command == "retrieve":
        #     return await self._retrieve_information(request)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "extract_triples",
                    "detect_document_type",
                    "preprocess_document",
                    "run_ner_el",
                    "run_relation_extraction",
                    "create_quadruples",
                    "process_file_to_ner",
                    # "retrieve",
                ],
            }

    async def _extract_triples(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract triples from text data."""
        try:
            # TODO: implement chunking for large contracts
            text = request.get("text", "")
            confidence_threshold = request.get("confidence_threshold", 0.7)
            max_triples = request.get("max_triples", 100)
            document_id = request.get("document_id", "")

            preprocessed_text = await self._preprocess_document(
                {
                    "document_content": text,
                    "document_type": "markdown",
                }
            )

            # TODO: set up additional prompt text and where it goes
            additional_prompt_text = request.get("additional_prompt_text", "")

            # Load default schema from JSON file
            schema_file_path = os.path.join(
                os.path.dirname(__file__), "default_schema.json"
            )
            with open(schema_file_path, "r") as f:
                default_schema = json.load(f)

            entities_list = request.get(
                "entities_list", default_schema["entities_list"]
            )

            if not preprocessed_text:
                return {"error": "Missing text parameter"}

            # Use the extract_triples tool
            result = await self._tools["extract_triples"].execute_tool(
                {
                    "text": preprocessed_text["data"]["processed_content"],
                    "confidence_threshold": confidence_threshold,
                    "max_triples": max_triples,
                    "entities_list": entities_list,
                    "document_id": document_id,
                }
            )

            # Insert triples into Neo4j if extraction was successful
            triples = result.get("triples", [])
            if triples:
                pass
                # self._graphdb_.insert_triples(triples)

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error extracting triples: {str(e)}")
            return {"status": "error", "message": f"Error extracting triples: {str(e)}"}

    async def _detect_document_type(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Detect document type from content, filename, or MIME type."""
        try:
            document_content = request.get("document_content", "")
            filename = request.get("filename", "")
            content_type = request.get("content_type", "")
            file_path = request.get("file_path", "")

            if not document_content and not file_path:
                return {"error": "Missing document_content or file_path parameter"}

            # Use the detect_document_type tool
            result = await self._tools["detect_document_type"].execute_tool(
                {
                    "document_content": document_content,
                    "filename": filename,
                    "content_type": content_type,
                    "file_path": file_path,
                }
            )

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error detecting document type: {str(e)}")
            return {
                "status": "error",
                "message": f"Error detecting document type: {str(e)}",
            }

    async def _preprocess_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess document content for knowledge extraction."""
        try:
            document_content = request.get("document_content", "")
            document_type = request.get("document_type", "")
            remove_stopwords = request.get("remove_stopwords", False)
            normalize_text = request.get("normalize_text", True)
            file_path = request.get("file_path", "")

            if not document_content and not file_path:
                return {"error": "Missing document_content or file_path parameter"}

            if not document_type:
                return {"error": "Missing document_type parameter"}

            # Use the preprocess_document tool
            result = await self._tools["preprocess_document"].execute_tool(
                {
                    "document_content": document_content,
                    "document_type": document_type,
                    "remove_stopwords": remove_stopwords,
                    "normalize_text": normalize_text,
                    "file_path": file_path,
                }
            )

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error preprocessing document: {str(e)}")
            return {
                "status": "error",
                "message": f"Error preprocessing document: {str(e)}",
            }

    async def _run_ner_el(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run Named Entity Recognition and Entity Linking on preprocessed text."""
        try:
            text = request.get("text", "")
            if not text:
                return {"error": "Missing text parameter"}
            entity_types = request.get(
                "entity_types",
                [
                    "PERSON",
                    "ORGANIZATION",
                    "LOCATION",
                    "DATE",
                    "ABSTRACT_TIME",
                    "MONEY",
                    "PRODUCT",
                ],
            )
            confidence_threshold = request.get("confidence_threshold", 0.8)
            enable_linking = request.get("enable_linking", True)
            chunk_size = request.get("chunk_size", 2000)
            enable_logging = request.get("enable_logging", False)
            for_retrieval = request.get("for_retrieval", False)
            log_file_path = request.get("log_file_path", "/app/logs")
            log_file_name = request.get("log_file_name", "")

            # Use the NER+EL tool
            tool_args = {
                "preprocessed_content": text,
                "entity_types": entity_types,
                "confidence_threshold": confidence_threshold,
                "enable_linking": enable_linking,
                "chunk_size": chunk_size,
                "enable_logging": enable_logging,
                "for_retrieval": for_retrieval,
                "log_file_path": log_file_path,
            }

            # Add log file name if provided
            if log_file_name:
                tool_args["log_file_name"] = log_file_name

            result = await self._tools["run_ner_el"].execute_tool(tool_args)

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error running NER+EL: {str(e)}")
            return {"status": "error", "message": f"Error running NER+EL: {str(e)}"}

    async def _run_relation_extraction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships between entities from preprocessed text using GPT-4o."""
        try:
            text = request.get("text", "")
            relation_types = request.get("relation_types", [])
            confidence_threshold = request.get("confidence_threshold", 0.7)
            chunk_size = request.get("chunk_size", 2000)
            enable_logging = request.get("enable_logging", False)
            log_file_path = request.get("log_file_path", "/app/logs")
            log_file_name = request.get("log_file_name", "")

            if not text:
                return {"error": "Missing text parameter"}

            # Use the relation extraction tool
            tool_args = {
                "preprocessed_content": text,
                "relation_types": relation_types,
                "confidence_threshold": confidence_threshold,
                "chunk_size": chunk_size,
                "enable_logging": enable_logging,
                "log_file_path": log_file_path,
            }

            # Add log file name if provided
            if log_file_name:
                tool_args["log_file_name"] = log_file_name

            result = await self._tools["run_relation_extraction"].execute_tool(
                tool_args
            )

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error running relation extraction: {str(e)}")
            return {
                "status": "error",
                "message": f"Error running relation extraction: {str(e)}",
            }

    async def _create_quadruples(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create quadruples from relation extraction and NER+EL results."""
        try:
            relations = request.get("relations", [])
            entities = request.get("entities", [])

            if not relations:
                return {"error": "Missing relations parameter"}
            if not entities:
                return {"error": "Missing entities parameter"}

            # Placeholder implementation
            result = {
                "quadruples": [],
                "total_found": 0,
                "message": "Placeholder implementation",
            }

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error creating quadruples: {str(e)}")
            return {
                "status": "error",
                "message": f"Error creating quadruples: {str(e)}",
            }

    async def _process_file_to_ner(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Complete pipeline: file -> preprocessing -> NER+EL"""
        try:
            # Extract parameters
            file_path = request.get("file_path", "")
            auto_detect_type = request.get("auto_detect_type", True)
            document_type = request.get("document_type", "")
            entity_types = request.get(
                "entity_types", ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY"]
            )
            relation_types = request.get("relation_types", [])
            ner_confidence_threshold = request.get("ner_confidence_threshold", 0.8)
            re_confidence_threshold = request.get("re_confidence_threshold", 0.7)
            enable_linking = request.get("enable_linking", True)
            remove_stopwords = request.get("remove_stopwords", False)
            normalize_text = request.get("normalize_text", True)
            enable_logging = request.get("enable_logging", False)
            log_file_path = request.get("log_file_path", "/app/logs")
            log_file_name = request.get("log_file_name", "")

            if not file_path:
                return {"error": "Missing file_path parameter"}

            # Initialize pipeline tracking
            import time

            pipeline_start_time = time.time()
            logger.info(f"Starting file-to-NER pipeline for: {file_path}")

            pipeline_results = {
                "file_path": file_path,
                "steps_completed": [],
                "processing_time": {},
                "pipeline_start_time": pipeline_start_time,
            }

            # Step 1: Document Type Detection (if auto_detect_type is True)
            if auto_detect_type:
                logger.info("Step 1: Detecting document type...")
                step_start = time.time()

                detect_request = {
                    "command": "detect_document_type",
                    "file_path": file_path,
                }

                detect_result = await self.process_request(detect_request)
                step_time = time.time() - step_start
                pipeline_results["processing_time"]["detection"] = step_time

                if detect_result["status"] != "success":
                    return {
                        "status": "error",
                        "message": f"Document type detection failed: {detect_result.get('message', 'Unknown error')}",
                        "pipeline_results": pipeline_results,
                    }

                # Use structure_type for preprocessing, not document_type
                detected_structure = detect_result["data"]["structure_type"]
                detected_file_type = detect_result["data"]["document_type"]

                pipeline_results["steps_completed"].append(
                    {
                        "step": "document_detection",
                        "result": f"file_type: {detected_file_type}, structure: {detected_structure}",
                        "processing_time": step_time,
                    }
                )

                # Use structure type for preprocessing
                document_type = detected_structure
                logger.info(f"Document type detected: {document_type}")
            else:
                if not document_type:
                    return {
                        "error": "document_type parameter required when auto_detect_type is false"
                    }
                pipeline_results["steps_completed"].append(
                    {
                        "step": "document_detection",
                        "result": f"manual override: {document_type}",
                        "processing_time": 0,
                    }
                )

            # Step 2: Preprocessing
            logger.info("Step 2: Preprocessing document...")
            step_start = time.time()

            preprocess_request = {
                "command": "preprocess_document",
                "file_path": file_path,
                "document_type": document_type,
                "remove_stopwords": remove_stopwords,
                "normalize_text": normalize_text,
            }

            preprocess_result = await self.process_request(preprocess_request)
            step_time = time.time() - step_start
            pipeline_results["processing_time"]["preprocessing"] = step_time

            if preprocess_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Preprocessing failed: {preprocess_result.get('message', 'Unknown error')}",
                    "pipeline_results": pipeline_results,
                }

            # Debug: log the preprocessing result structure
            logger.info(
                f"Preprocessing result keys: {list(preprocess_result.get('data', {}).keys())}"
            )
            logger.debug(f"Full preprocessing result: {preprocess_result}")

            # Handle different possible response structures from preprocessing
            preprocess_data = preprocess_result.get("data", {})

            if "processed_content" in preprocess_data:
                preprocessed_content = preprocess_data["processed_content"]
            elif "preprocessed_content" in preprocess_data:
                preprocessed_content = preprocess_data["preprocessed_content"]
            elif "content" in preprocess_data:
                preprocessed_content = preprocess_data["content"]
            else:
                # If no content found, log available keys and return error
                available_keys = list(preprocess_data.keys())
                logger.error(
                    f"No preprocessed content found. Available keys: {available_keys}"
                )
                return {
                    "status": "error",
                    "message": f"Preprocessing did not return expected content. Available keys: {available_keys}",
                    "pipeline_results": pipeline_results,
                }

            preprocessing_metadata = preprocess_data.get("metadata", {})

            pipeline_results["steps_completed"].append(
                {
                    "step": "preprocessing",
                    "result": {
                        "content_length": len(preprocessed_content),
                        "original_length": preprocessing_metadata.get(
                            "original_length", 0
                        ),
                        "processing_type": preprocessing_metadata.get(
                            "processing_type", "unknown"
                        ),
                    },
                    "processing_time": step_time,
                }
            )

            logger.info(
                f"Preprocessing completed: {len(preprocessed_content)} characters"
            )

            # Step 3: NER+EL
            logger.info("Step 3: Running NER+EL...")
            step_start = time.time()

            ner_request = {
                "command": "run_ner_el",
                "text": preprocessed_content,
                "entity_types": entity_types,
                "confidence_threshold": ner_confidence_threshold,
                "enable_linking": enable_linking,
                "enable_logging": enable_logging,
                "log_file_path": log_file_path,
            }

            # Add custom log file name if provided
            if log_file_name:
                ner_request["log_file_name"] = log_file_name

            ner_result = await self.process_request(ner_request)
            step_time = time.time() - step_start
            pipeline_results["processing_time"]["ner_el"] = step_time

            # Debug the NER result structure
            logger.info(f"NER result type: {type(ner_result)}")
            logger.info(
                f"NER result keys: {list(ner_result.keys()) if isinstance(ner_result, dict) else 'Not a dict'}"
            )

            # Handle different response formats
            if isinstance(ner_result, dict):
                if "status" in ner_result:
                    # Standard wrapped response
                    if ner_result["status"] != "success":
                        return {
                            "status": "error",
                            "message": f"NER+EL failed: {ner_result.get('message', 'Unknown error')}",
                            "pipeline_results": pipeline_results,
                        }
                    ner_data = ner_result["data"]
                elif "success" in ner_result:
                    # Direct tool response format
                    if not ner_result["success"]:
                        return {
                            "status": "error",
                            "message": f"NER+EL failed: {ner_result.get('error', 'Unknown error')}",
                            "pipeline_results": pipeline_results,
                        }
                    ner_data = ner_result
                else:
                    # Unexpected format
                    return {
                        "status": "error",
                        "message": f"NER+EL returned unexpected format: {ner_result}",
                        "pipeline_results": pipeline_results,
                    }
            else:
                return {
                    "status": "error",
                    "message": f"NER+EL returned non-dict result: {type(ner_result)}",
                    "pipeline_results": pipeline_results,
                }

            pipeline_results["steps_completed"].append(
                {
                    "step": "ner_el",
                    "result": {
                        "total_entities": ner_data.get("total_entities", 0),
                        "high_confidence_entities": ner_data.get(
                            "high_confidence_entities", 0
                        ),
                        "entity_types_found": ner_data.get("entity_types_found", []),
                        "relationships_count": len(ner_data.get("relationships", [])),
                    },
                    "processing_time": step_time,
                }
            )

            logger.info(
                f"NER+EL completed: {ner_data.get('total_entities', 0)} entities found"
            )

            # Step 4: Relation Extraction
            logger.info("Step 4: Running Relation Extraction...")
            step_start = time.time()

            re_request = {
                "command": "run_relation_extraction",
                "text": preprocessed_content,
                "relation_types": relation_types,
                "confidence_threshold": re_confidence_threshold,
                "enable_logging": enable_logging,
                "log_file_path": log_file_path,
            }

            # Add custom log file name if provided
            if log_file_name:
                re_request["log_file_name"] = log_file_name

            re_result = await self.process_request(re_request)
            step_time = time.time() - step_start
            pipeline_results["processing_time"]["relation_extraction"] = step_time

            # Handle different response formats for RE
            if isinstance(re_result, dict):
                if "status" in re_result:
                    # Standard wrapped response
                    if re_result["status"] != "success":
                        return {
                            "status": "error",
                            "message": f"Relation extraction failed: {re_result.get('message', 'Unknown error')}",
                            "pipeline_results": pipeline_results,
                        }
                    re_data = re_result["data"]
                elif "success" in re_result:
                    # Direct tool response format
                    if not re_result["success"]:
                        return {
                            "status": "error",
                            "message": f"Relation extraction failed: {re_result.get('error', 'Unknown error')}",
                            "pipeline_results": pipeline_results,
                        }
                    re_data = re_result
                else:
                    # Unexpected format
                    return {
                        "status": "error",
                        "message": f"Relation extraction returned unexpected format: {re_result}",
                        "pipeline_results": pipeline_results,
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Relation extraction returned non-dict result: {type(re_result)}",
                    "pipeline_results": pipeline_results,
                }

            pipeline_results["steps_completed"].append(
                {
                    "step": "relation_extraction",
                    "result": {
                        "total_relationships": re_data.get("total_found", 0),
                        "high_confidence_relationships": re_data.get(
                            "processing_stats", {}
                        ).get("high_confidence_relationships", 0),
                        "relationship_types": list(
                            re_data.get("metadata", {})
                            .get("relationship_types", {})
                            .keys()
                        ),
                        "processing_errors": re_data.get("processing_stats", {}).get(
                            "processing_errors", 0
                        ),
                    },
                    "processing_time": step_time,
                }
            )

            logger.info(
                f"Relation extraction completed: {re_data.get('total_found', 0)} relationships found"
            )

            # Calculate total processing time
            total_time = sum(pipeline_results["processing_time"].values())
            pipeline_results["total_processing_time"] = total_time

            # Prepare final result
            final_result = {
                "entities": ner_data.get("entities", []),
                "ner_relationships": ner_data.get("relationships", []),
                "extracted_relationships": re_data.get("relationships", []),
                "statistics": {
                    "ner_stats": ner_data.get("statistics", {}),
                    "re_stats": re_data.get("processing_stats", {}),
                },
                "entity_types_found": ner_data.get("entity_types_found", []),
                "total_entities": ner_data.get("total_entities", 0),
                "high_confidence_entities": ner_data.get("high_confidence_entities", 0),
                "total_relationships": re_data.get("total_found", 0),
                "high_confidence_relationships": re_data.get(
                    "processing_stats", {}
                ).get("high_confidence_relationships", 0),
                "pipeline_metadata": {
                    "file_path": file_path,
                    "document_type": document_type,
                    "preprocessing_metadata": preprocessing_metadata,
                    "pipeline_results": pipeline_results,
                    "total_processing_time": total_time,
                },
                "success": True,
            }

            logger.info(
                f"File-to-NER-RE pipeline completed successfully in {total_time:.2f}s"
            )

            final_response = {"status": "success", "data": final_result}

            # Log the final pipeline result if logging is enabled
            if enable_logging:
                await self._log_pipeline_result(
                    final_response, log_file_path, log_file_name
                )

            return final_response

        except Exception as e:
            logger.error(f"Error in file-to-NER-RE pipeline: {str(e)}")
            return {
                "status": "error",
                "message": f"File-to-NER-RE pipeline failed: {str(e)}",
                "pipeline_results": (
                    pipeline_results if "pipeline_results" in locals() else {}
                ),
            }

    async def _log_pipeline_result(
        self, final_response: Dict[str, Any], log_file_path: str, log_file_name: str
    ) -> None:
        """Log the exact pipeline response that's sent to clients"""
        try:
            import json
            import os
            from datetime import datetime

            # Generate log file name if not provided
            if not log_file_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_name = f"pipeline_{timestamp}.log"

            # Ensure log directory exists
            os.makedirs(log_file_path, exist_ok=True)

            log_file_full_path = os.path.join(log_file_path, log_file_name)

            # Write to log file with delimiter and exact response
            with open(log_file_full_path, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 100 + "\n")  # Line delimiter
                f.write("FINAL CLIENT RESPONSE:\n")
                f.write(json.dumps(final_response, indent=2, ensure_ascii=False) + "\n")
                f.write("=" * 100 + "\n")  # Final separator

            logger.info(f"Final pipeline response logged to: {log_file_full_path}")

        except Exception as e:
            logger.error(f"Error logging pipeline result: {e}")

    async def _classify_intent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the intent of a user query into one of several categories."""
        confidence_threshold = 0.6
        query = request.get("query")
        if not query:
            raise ValueError("Missing required parameter: query")

        intent = request.get("intent")
        allowed_intents = ["comparative", "fact seeking", "aggregative", "explanatory"]

        if intent and intent in allowed_intents:
            return {
                "intent": intent,
                "confidence": 0.99,
            }

        # TODO: very much need to improve prompt for this if it fails, currently it is zero shotting
        # output: {"intent": "fact seeking", "confidence": 0.95}
        prompt = prompt_service.get_intent_classification_prompt(query=query)
        full_prompt = prompt["system"] + "\n\n" + prompt["user"]

        response = await llm_service.simple_completion(
            prompt=full_prompt, response_format={"type": "json_object"}
        )

        # returns json as string, convert to dict
        response = json.loads(response) if isinstance(response, str) else response

        if (
            not response
            or response["intent"] not in allowed_intents
            or float(response["confidence"]) < confidence_threshold
        ):
            raise ValueError(
                "Invalid intent found: "
                + response["intent"]
                + " with confidence: "
                + str(response["confidence"])
            )

        return response

    # async def _execute_cypher_query(self, cypher_query: str) -> Dict[str, Any]:
    #     response = await self._graphdb_.execute_cypher_query(cypher_query)
    #     # logger.warning(f"Cypher response: {response}")
    #     return response

    # async def _retrieve_information(self, request: Dict[str, Any]) -> Any:
    #     """Main retrieval method that follows the 4-step pipeline.

    #     Args:
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     request: Dictionary containing the request parameters
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     - query: The user's natural language query (required)

    #     Returns:
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     Dict containing:
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     - intent: Result from _classify_intent
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     - results: List of retrieved information
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     - metadata: Additional execution metadata

    #     Raises:
    #                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     ValueError: If required parameters are missing
    #     """
    #     log_response = True
    #     try:
    #         # Step 1: Intent and entity recognition
    #         # intent
    #         # error handling for intent confidence being low or intent not being in allowed_intents is in classify_intent
    #         # parallelize step 1 with 2 lambdas: 1 for classify intent and one for ner
    #         intent_info = await self._classify_intent(request)
    #         # logger.info(
    #         #     f"INTENT_INFO: {intent_info['intent']} with confidence: {intent_info['confidence']}"
    #         # )
    #         intent = intent_info["intent"]
    #         intent_confidence = intent_info["confidence"]
    #         request["intent"] = intent
    #         request["intent_confidence"] = intent_confidence

    #         request["text"] = request["query"]
    #         request["for_retrieval"] = True
    #         # entity/relationship extraction
    #         ner_el_info = await self._run_ner_el(request)
    #         if ner_el_info["status"] != "success":
    #             raise ValueError("NER+EL failed")
    #         entities = ner_el_info["data"]["entities"]
    #         relationships = ner_el_info["data"]["relationships"]

    #         logger.info(
    #             f"NER_EL_INFO: \nEntities:{ner_el_info['data']['entities']} \nRelationships:{ner_el_info['data']['relationships']}"
    #         )

    #         # Step 1->2: Entity linking and reconciliation
    #         # have lookup table
    #         # may need vectorized lookup -> kg

    #         # Step 2: Multi-strategy retrieval
    #         # Entity Traversal

    #         all_cypher_results = []
    #         for entity in entities:
    #             entity_name = entity.get("text")
    #             if entity_name:
    #                 # Construct Cypher query for the extracted entity
    #                 # Note: This assumes a direct match between extracted entity text and Neo4j entity name.
    #                 # As discussed, exact matching with URIs might be an issue.
    #                 cypher_query = f"""
    # 				MATCH (label_entity:Entity {{name: \"{entity_name}\"}})
    # 				OPTIONAL MATCH (uri_entity:Entity)-[label_rel:RELATION {{type: \"http://www.w3.org/2000/01/rdf-schema#label\"}}]->(label_entity)
    # 				WITH COALESCE(uri_entity, label_entity) AS start_node
    # 				MATCH (start_node)-[r]-(n)
    # 				RETURN start_node.name AS Source, r.type AS RelationshipType, n.name AS TargetName
    # 				LIMIT 10
    # 				"""
    #                 logger.info(
    #                     f"Executing Cypher query for entity '{entity_name}': {cypher_query}"
    #                 )
    #                 cypher_response = await self._graphdb_.execute_cypher_query(
    #                     cypher_query
    #                 )
    #                 all_cypher_results.append(
    #                     {
    #                         "entity": entity_name,
    #                         "query": cypher_query,
    #                         "results": cypher_response,
    #                     }
    #                 )

    #         # Write all Cypher query results to a log file
    #         if log_response:
    #             log_file_path = "logs/cypher_query_results.log"
    #             with open(log_file_path, "w", encoding="utf-8") as f:
    #                 f.write(
    #                     json.dumps(all_cypher_results, indent=2, ensure_ascii=False)
    #                 )
    #                 f.write("\n")
    #             logger.info(f"Wrote all Cypher query results to {log_file_path}")

    #         # todo: Semantic/Vector Search
    #         # todo: Tool generator agent: Cypher generation

    #         # Step 3: Result processing and ranking
    #         # Step 4: Context optimization

    #         return {
    #             "intent": intent,
    #             "intent_confidence": intent_confidence,
    #             "extracted_entities": entities,
    #             "extracted_relationships": relationships,
    #             # "results": [],  # Will contain final results
    #             # "metadata": {},  # Will contain execution metadata
    #         }

    #     except ValueError as e:
    #         return {"error": str(e), "available_parameters": ["query"]}

    @property
    def agent_id_str(self) -> str:
        return self._agent_id_str

    @property
    def uuid(self) -> UUID:
        if self._uuid is None:
            raise ValueError("UUID has not been set yet.")
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID):
        if self._uuid is not None:
            raise ValueError("UUID can only be set once.")
        self._uuid = value

    @property
    def name(self) -> str:
        """Agent's unique identifier."""
        return self._name

    @property
    def description(self) -> str:
        """KG Agent will extract triples from text data and insert them into the graph database."""
        return self._description

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        # Initialize tools if needed
        for tool_name, tool in self._tools.items():
            if hasattr(tool, "initialize"):
                await tool.initialize(config)

        self._initialized = True
        logger.info("KnowledgeGraphExtractionAgent initialized successfully")

    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._initialized = False
        logger.info("KnowledgeGraphExtractionAgent shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        return {
            "initialized": self._initialized,
            "healthy": self._initialized,
            "tools_available": list(self._tools.keys()),
            "capabilities": self.get_tools(),
        }
