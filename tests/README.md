# Test Suite

Simple, comprehensive test suite for the MCP multi-agent system. Tests configuration, server endpoints, LLM service, agent functionality, registry system, and core components.

## Usage

```bash
# Run all tests
./test

# Run specific categories
./test config       # Configuration tests
./test server       # Server endpoint tests
./test llm         # LLM service tests
./test agents       # Agent functionality tests
./test services     # Service layer tests (includes LLM & prompt services)
./test registry     # Registry system tests
./test tools        # Agent tools tests (experimental)
./test unit        # Unit tests only
./test integration # Integration tests only
```

## Test Coverage (110+ tests, 90+ passing)

### Configuration Tests (12 tests) ✅
**What**: Configuration parsing, provider setup, environment variables
- `test_parse_valid_default_model` - Parse "provider:model" format correctly
- `test_parse_default_model_no_colon` - Parse provider-only format
- `test_parse_empty_default_model` - Handle empty model configuration
- `test_get_openai_provider_config` - Retrieve OpenAI provider configuration
- `test_get_claude_provider_config` - Retrieve Claude provider configuration
- `test_get_invalid_provider_config` - Handle invalid provider requests
- `test_get_provider_available_models` - Get available models for provider
- `test_get_provider_default_model` - Get default model for provider
- `test_get_invalid_provider_models` - Handle invalid provider model requests
- `test_api_keys_with_patching` - API key loading with proper mocking
- `test_missing_api_key_handling` - Handle missing API keys gracefully
- `test_config_supports_llm_service_initialization` - Config integration with LLM service

### Server Endpoint Tests (12 tests) ✅
**What**: FastAPI server endpoints, error handling, API responses
- `test_health_endpoint_returns_200` - Health endpoint responds with 200
- `test_health_endpoint_structure` - Health endpoint returns expected fields
- `test_list_agents_endpoint` - Agents listing endpoint works
- `test_list_agents_contains_valid_agents` - Agent data has correct structure
- `test_mcp_resources_endpoint` - MCP resources endpoint returns proper format
- `test_nonexistent_endpoint_returns_404` - Invalid endpoints return 404
- `test_invalid_agent_id_returns_400` - Invalid agent IDs return 400
- `test_nonexistent_agent_returns_404` - Missing agents return 404
- `test_tool_generator_missing_query` - Tool generator validates query parameter
- `test_tool_generator_missing_data` - Tool generator validates data parameter
- `test_docs_endpoint_accessible` - OpenAPI docs are accessible
- `test_openapi_json_accessible` - OpenAPI JSON schema is accessible

### LLM Service Tests (19 tests) ✅
**What**: LLM provider management, completions, model switching
- `test_service_initialization_with_providers` - Service initializes with multiple providers
- `test_service_initialization_openai_only` - Service works with OpenAI only
- `test_service_initialization_with_explicit_provider` - Override default provider
- `test_set_provider_success` - Switch between providers successfully
- `test_set_provider_invalid` - Handle invalid provider switches
- `test_get_available_providers` - List all available providers
- `test_chat_completion_basic` - Basic chat completion functionality
- `test_chat_completion_with_parameters` - Chat completion with custom parameters
- `test_chat_completion_with_provider_override` - Override provider per request
- `test_chat_completion_no_provider` - Handle missing provider errors
- `test_simple_completion_basic` - Basic simple completion functionality
- `test_simple_completion_with_parameters` - Simple completion with parameters
- `test_default_model_used_when_none_specified` - Use configured default model
- `test_default_model_provider_only` - Handle provider-only defaults
- `test_validate_all_providers` - Validate all registered providers
- `test_validate_providers_with_failure` - Handle provider validation failures
- `test_get_provider_info` - Get detailed provider information
- `test_service_ready_for_use` - Service is ready for typical usage
- `test_end_to_end_completion_flow` - Complete workflow from init to completion

### Agent Tests (44 tests) ✅

#### Knowledge Graph Agent (19 tests) ✅
**What**: Knowledge Graph Agent functionality, document processing, triple extraction
- `test_agent_creation` - Basic agent creation and properties
- `test_uuid_property` - UUID property management and validation
- `test_agent_initialization` - Agent initialization with configuration
- `test_agent_shutdown` - Clean agent shutdown process
- `test_get_status` - Agent status and health reporting
- `test_get_capabilities` - Agent capabilities listing
- `test_tools_available` - Tool availability verification
- `test_process_request_uninitialized` - Handle requests when not initialized
- `test_process_request_unknown_command` - Handle unknown command requests
- `test_process_extract_triples_request` - Triple extraction request processing
- `test_process_detect_document_request` - Document type detection processing
- `test_process_preprocess_document_request` - Document preprocessing
- `test_ner_el_integration` - Named Entity Recognition integration
- `test_relation_extraction_integration` - Relation extraction integration
- `test_tool_error_handling` - Tool failure error handling
- `test_document_processing_workflow` - End-to-end document processing
- `test_ner_to_relation_workflow` - NER to relation extraction workflow
- `test_neo4j_service_available` - Neo4j database service integration
- `test_agent_ready_for_production` - Production readiness verification

#### Tool Generator Agent (25 tests) ✅
**What**: Dynamic tool creation, complexity assessment, code generation and execution
- `test_agent_creation` - Basic agent creation and properties
- `test_agent_initialization` - Agent initialization with OpenAI API key
- `test_agent_initialization_no_api_key` - Handle missing API key requirement
- `test_agent_shutdown` - Agent shutdown process
- `test_get_status` - Agent status reporting with tool counts
- `test_get_capabilities` - Agent capabilities for tool generation
- `test_debug_logging` - Debug logging functionality
- `test_process_request_uninitialized` - Handle requests when not initialized
- `test_process_request_unknown_command` - Handle unknown command requests
- `test_assess_complexity_request` - Query complexity assessment
- `test_generate_direct_request` - Direct tool generation for simple queries
- `test_generate_and_execute_request` - Complete generation and execution workflow
- `test_get_pending_tools` - Retrieve pending tools awaiting approval
- `test_approve_tool` - Approve pending tools for use
- `test_reject_tool` - Reject unsuitable tools
- `test_get_approved_tools` - Retrieve approved tools list
- `test_approve_nonexistent_tool` - Handle approval of non-existent tools
- `test_execute_code_basic` - Basic code execution functionality
- `test_execute_code_with_data` - Code execution with data parameters
- `test_execute_code_error_handling` - Error handling in code execution
- `test_simple_tool_generation_workflow` - End-to-end simple tool generation
- `test_tool_approval_workflow` - Complete tool approval workflow
- `test_agent_ready_for_production` - Production readiness verification
- `test_session_management` - Session ID generation and management
- `test_error_resilience` - Agent resilience to error conditions

### Registry System Tests (18 tests) ✅
**What**: Agent registration, registry data models, lifecycle management
- `test_agent_status_values` - Enum values for agent status
- `test_agent_status_comparison` - Status comparison operations
- `test_agent_info_creation` - Agent information model creation
- `test_agent_info_with_custom_status` - Custom status handling
- `test_registry_creation` - Basic registry initialization
- `test_add_agent` - Agent registration process
- `test_add_multiple_agents` - Multiple agent management
- `test_register_single_agent` - Complete agent registration workflow
- `test_register_multiple_agents` - Multiple agent registration
- `test_deterministic_uuid_generation` - Consistent UUID generation
- `test_agent_initialization_called` - Proper agent initialization
- `test_agent_uuid_assignment` - UUID assignment verification
- `test_registry_internal_consistency` - Registry state consistency
- `test_agent_class_instantiation` - Agent class instantiation
- `test_config_passing` - Configuration passing to agents
- `test_registry_state_after_registration` - Post-registration state

### Service Layer Tests (8+ tests) ⚠️
**What**: Core service functionality including prompt service
- **Prompt Service**: Prompt generation and template management (some tests need import fixes)
- **Additional services**: Ready for expansion

### Agent Tools Tests (Experimental) ⚠️
**What**: Individual agent tool functionality
- **Document Detection Tool**: Basic functionality tests
- **Triple Extraction Tool**: Core extraction logic tests
- **Note**: Some tests need import system fixes for full functionality

## Test Architecture

- **Unit tests**: Individual component testing with mocks
- **Integration tests**: API endpoint and service interaction testing
- **Fixtures**: Reusable test data and mock objects in `conftest.py`
- **Markers**: `@pytest.mark.config`, `@pytest.mark.server`, `@pytest.mark.llm`, `@pytest.mark.agents`, `@pytest.mark.registry`, `@pytest.mark.services`, `@pytest.mark.tools`
- **Async support**: Full async/await testing with pytest-asyncio

## Test Status

✅ **90+ tests passing** - Core functionality well tested
⚠️ **20 tests with import issues** - Tool and service tests need refinement
🎯 **Solid foundation** - Ready for expansion and refinement

## Adding Tests

1. Create test files in appropriate directories (`tests/test_*.py`)
2. Use existing fixtures from `conftest.py`
3. Add pytest markers for categorization
4. Follow naming convention: `test_<what_it_tests>`
5. Keep test methods simple and focused on one thing

## Quick Start

```bash
# Run all working tests
./test unit

# Run specific components
./test agents
./test registry
./test llm

# Run everything (including experimental)
./test
```