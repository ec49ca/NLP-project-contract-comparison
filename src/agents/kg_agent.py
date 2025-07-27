"""
Knowledge Graph Agent - Triple Extraction Implementation

This agent provides knowledge graph capabilities starting with triple extraction from client data.
Additional tools to be implemented:

## Core Tools to Implement:

1. **Triple Creation & Management**
   - extract_triples
   - create_triples_from_data - Convert structured data (JSON, CSV) to triples
   - validate_triples - Validate and normalize triples

2. **Graph Traversal & Querying**
   - find_relationships
   - traverse_graph

How tools work:
1. Discovery: client hits /agents/discover to get a list of agents with basic info and tools available
        - agentdiscoveryrequest with filters. each agent returns tools via .get_tools()
2. Tool discovery:
"""

# TODO: Parallelize all gpt prompts for better scatter gather.
# TODO: (experiment with this, maybe it is already correct, but don't know for sure) ner_el_tool does not need to only extract entities. it can also get relationships but because of bad prompting it only gets simple relationships. this was initially the reason i created the relation_extraction tool, but it is redundant (test this assumption as well)
# TODO: remove entity types dependence


import logging
from typing import Dict, List, Any, Optional
from ..interfaces.agent import AgentInterface
from .tools.extract_triples import ExtractTriplesTool
from .tools.detect_document_tool import DetectDocumentTool
from .tools.ner_el_tool import NEREntityLinkingTool
from .tools.preprocess_document_tool import PreprocessDocumentTool
from .tools.relation_extraction_tool import RelationExtractionTool
from ..services.neo4j_service import Neo4jService
from ..services.llm_service import llm_service
from ..services.prompt_service import prompt_service
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent(AgentInterface):
    """Knowledge graph agent for triple extraction and graph operations"""

    def __init__(self):
        self._agent_id_str = "knowledge_graph"
        self._uuid = None
        self.agent_id = "knowledge_graph"
        self._name = "Knowledge Graph Agent"
        self._description = "Extract triples from data and perform graph operations"
        self._initialized = False
        self.category = "knowledge_management"
        self.status = "initialized"
        self._tools = {}
        self._graphdb_ = Neo4jService()

        # Add extract_triples tool
        self._tools["extract_triples"] = ExtractTriplesTool()

        # Add detect_document_type tool
        self._tools["detect_document_type"] = DetectDocumentTool()

        # Add preprocess_document tool
        self._tools["preprocess_document"] = PreprocessDocumentTool()

        # Add NER+EL tool
        self._tools["run_ner_el"] = NEREntityLinkingTool()

        # Add relation extraction tool
        self._tools["run_relation_extraction"] = RelationExtractionTool()

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
        logger.info("KnowledgeGraphAgent initialized successfully")

    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._initialized = False
        logger.info("KnowledgeGraphAgent shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        return {
            "initialized": self._initialized,
            "healthy": self._initialized,
            "tools_available": list(self._tools.keys()),
            "capabilities": self.get_capabilities(),
        }

    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Return agent's capabilities."""
        return [
            {
                "name": "extract_triples",
                "description": "Extract triples (subject-predicate-object relationships) from unstructured text",
                "parameters": {
                    "text": "Text to extract triples from (required)",
                    "confidence_threshold": "Minimum confidence score for triples (0.0-1.0, default: 0.7)",
                    "max_triples": "Maximum number of triples to extract (default: 100)",
                },
            },
            {
                "name": "detect_document_type",
                "description": "Detect document type with 7-point structure classification: highly_structured, structured, moderately_structured, semi_structured, lightly_structured, unstructured, highly_unstructured, plus scanned detection",
                "parameters": {
                    "document_content": "Document content or file path (required)",
                    "content_type": "MIME type hint (optional)",
                    "filename": "Original filename for extension-based detection (optional)",
                    "file_path": "Path to the file for analysis (optional, alternative to document_content)",
                },
            },
            {
                "name": "preprocess_document",
                "description": "Clean and preprocess document content for knowledge extraction with OCR support for scanned documents, type-specific preprocessing, text normalization, and stopword removal",
                "parameters": {
                    "document_content": "Raw document content (required if no file_path)",
                    "document_type": "Document type from detect_document_type (required) - use 'scanned' for OCR processing",
                    "remove_stopwords": "Whether to remove stopwords (default: false)",
                    "normalize_text": "Whether to normalize text (default: true)",
                    "file_path": "Path to file for OCR processing (optional, for scanned documents)",
                },
            },
            {
                "name": "run_ner_el",
                "description": "Advanced Named Entity Recognition and Entity Linking using GPT-4 on preprocessed text with chunking support and optional logging",
                "parameters": {
                    "text": "Preprocessed text content (required)",
                    "entity_types": "List of entity types to extract (optional, default: ['PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'MONEY']. Available: PERSON, ORGANIZATION, LOCATION, DATE, MONEY, PRODUCT, EMAIL, PHONE, ID_NUMBER, PERCENTAGE, QUANTITY, EVENT, DOCUMENT, JOB_TITLE, SKILL)",
                    "confidence_threshold": "Minimum confidence score for entities (0.0-1.0, default: 0.8)",
                    "enable_linking": "Whether to perform entity linking (default: true)",
                    "chunk_size": "Size of text chunks for processing (default: 2000)",
                    "enable_logging": "Whether to log query and output to file (default: false)",
                    "log_file_path": "Directory path for log files (default: '/app/logs')",
                    "log_file_name": "Custom log file name (optional, auto-generated if not provided)",
                },
            },
            {
                "name": "run_relation_extraction",
                "description": "Extract comprehensive relationships from preprocessed text using GPT-4o with rich metadata for RDF quadruples",
                "parameters": {
                    "text": "Preprocessed text content (required)",
                    "relation_types": "List of specific relation types to focus on (optional, default: extracts all types)",
                    "confidence_threshold": "Minimum confidence score for relations (0.0-1.0, default: 0.7)",
                    "chunk_size": "Size of text chunks for processing (default: 2000)",
                    "enable_logging": "Whether to log query and output to file (default: false)",
                    "log_file_path": "Directory path for log files (default: '/app/logs')",
                    "log_file_name": "Custom log file name (optional, auto-generated if not provided)",
                },
            },
            {
                "name": "create_quadruples",
                "description": "Create quadruples from relation extraction and NER+EL results",
                "parameters": {
                    "relations": "List of relations from run_relation_extraction (required)",
                    "entities": "List of entities from run_ner_el (required)",
                    "confidence_threshold": "Minimum confidence score for quadruples (0.0-1.0, default: 0.7)",
                    "max_quadruples": "Maximum number of quadruples to create (default: 100)",
                },
            },
            {
                "name": "process_file_to_ner",
                "description": "Complete pipeline: takes a file, preprocesses it, extracts entities using NER+EL, and extracts relationships using RE",
                "parameters": {
                    "file_path": "Path to the file to process (required)",
                    "auto_detect_type": "Whether to auto-detect document type (default: true)",
                    "document_type": "Manual document type override (optional, use if auto_detect_type is false)",
                    "entity_types": "List of entity types to extract (optional, default: ['PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'MONEY'])",
                    "relation_types": "List of relation types to focus on (optional, default: extracts all types)",
                    "ner_confidence_threshold": "Minimum confidence score for entities (0.0-1.0, default: 0.8)",
                    "re_confidence_threshold": "Minimum confidence score for relations (0.0-1.0, default: 0.7)",
                    "enable_linking": "Whether to perform entity linking (default: true)",
                    "remove_stopwords": "Whether to remove stopwords during preprocessing (default: false)",
                    "normalize_text": "Whether to normalize text during preprocessing (default: true)",
                    "enable_logging": "Whether to log processing steps and results (default: false)",
                    "log_file_path": "Directory path for log files (default: '/app/logs')",
                    "log_file_name": "Custom log file name (optional, auto-generated if not provided)",
                },
            },
            {
                "name": "retrieve",
                "description": "Retrieve information from the knowledge graph based on the user's query",
                "parameters": {
                    "query": "User query to retrieve information (required)",
                    "intent": "Intent of the user query (optional)",
                    "context": "Additional context for the query (optional)",
                },
            },
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
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
        elif command == "retrieve":
            return await self._retrieve_information(request)
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
                    "retrieve",
                ],
            }

    async def _extract_triples(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract triples from text data."""
        try:
            text = request.get("text", "")
            confidence_threshold = request.get("confidence_threshold", 0.7)
            max_triples = request.get("max_triples", 100)

            if not text:
                return {"error": "Missing text parameter"}

            # Use the extract_triples tool
            result = await self._tools["extract_triples"].execute_tool(
                {
                    "text": text,
                    "confidence_threshold": confidence_threshold,
                    "max_triples": max_triples,
                }
            )

            # Insert triples into Neo4j if extraction was successful
            triples = result.get("triples", [])
            if triples:
                self._graphdb_.insert_triples(triples)

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

        # returns 1 word for the intent
        # TODO: very much need to improve prompt for this if it fails, right it is zero shotting
        prompt = prompt_service.get_intent_classification_prompt(query)
        full_prompt = prompt["system"] + "\n\n" + prompt["user"]

        response = await llm_service.simple_completion(
            prompt=full_prompt, response_format={"type": "json_object"}
        )

        if (
            not response
            or response["intent"] not in allowed_intents
            or response["confidence"] < confidence_threshold
        ):
            raise ValueError(
                "Invalid intent found: "
                + response["intent"]
                + " with confidence: "
                + str(response["confidence"])
            )

        return response

    async def _retrieve_information(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main retrieval method that follows the 4-step pipeline.

        Args:
            request: Dictionary containing the request parameters
                - query: The user's natural language query (required)

        Returns:
            Dict containing:
                - intent: Result from _classify_intent
                - results: List of retrieved information
                - metadata: Additional execution metadata

        Raises:
            ValueError: If required parameters are missing
        """
        try:
            # Step 1: Intent and entity recognition
            # intent
            # error handling for intent confidence being low or intent not being in allowed_intents is in classify_intent
            # parallelize step 1 with 2 lambdas: 1 for classify intent and one for ner
            intent_info = await self._classify_intent(request)
            # logger.info(
            #     f"INTENT_INFO: {intent_info['intent']} with confidence: {intent_info['confidence']}"
            # )
            intent = intent_info["intent"]
            intent_confidence = intent_info["confidence"]
            request["intent"] = intent
            request["intent_confidence"] = intent_confidence

            request["text"] = request["query"]
            request["for_retrieval"] = True
            # entity/relationship extraction
            ner_el_info = await self._run_ner_el(request)
            with open("logs/ner_el_info_test", "w") as f:
                json.dump(ner_el_info, f)
            if ner_el_info["status"] != "success":
                raise ValueError("NER+EL failed")
            logger.warning(
                f"NER_EL_INFO: \nEntities:{ner_el_info['data']['entities']} \nRelationships:{ner_el_info['data']['relationships']}"
            )

            # TODO: Implement remaining steps
            # Step 2: Multi-strategy retrieval
            # Step 3: Result processing and ranking
            # Step 4: Context optimization

            return {
                "intent": intent,
                "intent_confidence": intent_confidence,
                "extracted_entities": ner_el_info["data"]["entities"],
                "extracted_relationships": ner_el_info["data"]["relationships"],
                "results": [],  # Will contain final results
                "metadata": {},  # Will contain execution metadata
            }

        except ValueError as e:
            return {"error": str(e), "available_parameters": ["query"]}
