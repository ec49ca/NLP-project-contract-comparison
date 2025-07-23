# Samvid MCP Server - API Endpoints Guide

Complete reference for all available API endpoints, request formats, and response examples.

---

## 🚀 **Base URL & Authentication**

- **Base URL**: `http://localhost:8000` (default)
- **Authentication**: None required (add authentication in production)
- **Content-Type**: `application/json` for POST requests
- **Interactive Docs**: `http://localhost:8000/docs`

---

## 📊 **Core Server Endpoints**

### **Health Check**
`GET /health`

Check server health and get basic statistics.

**Response:**
```json
{
  "status": "healthy",
  "server_initialized": true,
  "agents_count": 6,
  "active_agents": 6,
  "version": "0.1.0"
}
```

---

### **Interactive Documentation**
`GET /docs`

Access Swagger UI for interactive API testing and documentation.

---

## 🤖 **Agent Management**

### **List All Agents**
`GET /agents`

List all registered agents with their capabilities.

**Response:**
```json
{
  "total_agents": 6,
  "active_agents": 6,
  "agents": [
    {
      "name": "Knowledge Graph Agent",
      "description": "Extract triples from data and perform graph operations",
      "status": "active",
      "capabilities": [
        {
          "name": "extract_triples",
          "description": "Extract triples (subject-predicate-object relationships) from unstructured text",
          "parameters": {
            "text": "Text to extract triples from (required)",
            "confidence_threshold": "Minimum confidence score for triples (0.0-1.0, default: 0.7)",
            "max_triples": "Maximum number of triples to extract (default: 100)"
          }
        }
      ]
    }
  ]
}
```

---

### **Get Specific Agent**
`GET /agents/{agent_id}`

Get information about a specific agent by UUID.

**Parameters:**
- `agent_id` (path): Agent UUID

**Example:**
```bash
curl http://localhost:8000/agents/12345678-1234-5678-9abc-123456789abc
```

**Response:**
```json
{
  "agent_id": "12345678-1234-5678-9abc-123456789abc",
  "name": "Knowledge Graph Agent",
  "description": "Extract triples from data and perform graph operations",
  "status": "active"
}
```

---

### **Register New Agent**
`POST /agents`

Register a new agent instance (typically handled automatically).

**Request Body:**
```json
{
  "agent_class_name": "MyCustomAgent",
  "config": {
    "api_key": "your-key",
    "custom_setting": "value"
  }
}
```

**Response:**
```json
{
  "agent_id": "12345678-1234-5678-9abc-123456789abc"
}
```

---

## 🎯 **Agent Execution**

### **Execute Agent Capability**
`POST /execute/{agent_name}/{capability}`

Execute a specific capability of any agent.

**Parameters:**
- `agent_name` (path): Full agent name (e.g., "Knowledge Graph Agent")
- `capability` (path): Capability name (e.g., "extract_triples")
- Request body: Parameters specific to the capability

**Example:**
```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/extract_triples" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Inc. was founded by Steve Jobs in Cupertino, California.",
    "confidence_threshold": 0.8,
    "max_triples": 50
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "triples": [
      {
        "subject": "Apple Inc.",
        "predicate": "founded_by",
        "object": "Steve Jobs",
        "confidence": 0.95,
        "source": "relationship_extraction"
      },
      {
        "subject": "Apple Inc.",
        "predicate": "located_in",
        "object": "Cupertino, California",
        "confidence": 0.90,
        "source": "relationship_extraction"
      }
    ],
    "total_extracted": 2,
    "entities_found": 3,
    "relationships_found": 2
  }
}
```

---

### **Tool Generator Convenience Endpoint**
`POST /tool-generator/execute`

Convenience endpoint for dynamic tool generation.

**Request Body:**
```json
{
  "query": "Calculate the average of a list of numbers",
  "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "success": true,
    "function_code": "def calculate_average(data):\n    return sum(data) / len(data)",
    "output": 5.5,
    "metadata": {
      "intent_summary": "Calculate the average of a list of numbers",
      "capabilities": ["direct_generation"],
      "tags": ["simple", "direct"]
    }
  }
}
```

---

## 🔍 **Resource Discovery**

### **MCP Resources**
`GET /mcp/resources`

List all available MCP resources and capabilities.

**Response:**
```json
[
  {
    "name": "Knowledge Graph Agent.extract_triples",
    "description": "Extract triples (subject-predicate-object relationships) from unstructured text",
    "parameters": {
      "text": "Text to extract triples from (required)",
      "confidence_threshold": "Minimum confidence score for triples (0.0-1.0, default: 0.7)"
    },
    "type": "capability"
  },
  {
    "name": "Knowledge Graph Agent",
    "description": "Extract triples from data and perform graph operations",
    "type": "agent",
    "capabilities": [...]
  }
]
```

---

### **Auto-Discovery**
`POST /discover`

Trigger auto-discovery and registration of all available agents.

**Response:**
```json
{
  "discovered_agents": 6,
  "registered_agents": 6,
  "status": "success"
}
```

---

## 🤖 **Agent Capabilities Reference**

### **Knowledge Graph Agent**

#### `extract_triples`
Extract subject-predicate-object relationships from text.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/extract_triples" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Smith works at OpenAI in San Francisco.",
    "confidence_threshold": 0.7,
    "max_triples": 100
  }'
```

#### `detect_document_type`
Classify document structure on a 7-point scale.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/detect_document_type" \
  -H "Content-Type: application/json" \
  -d '{
    "document_content": "Invoice #12345\nDate: 2024-01-15\nCustomer: John Doe",
    "content_type": "text/plain"
  }'
```

#### `preprocess_document`
Clean and normalize documents with OCR support.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/preprocess_document" \
  -H "Content-Type: application/json" \
  -d '{
    "document_content": "Raw document text...",
    "document_type": "structured",
    "remove_stopwords": false,
    "normalize_text": true
  }'
```

#### `run_ner_el`
Named Entity Recognition + Entity Linking.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/run_ner_el" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Preprocessed document content...",
    "entity_types": ["PERSON", "ORGANIZATION", "LOCATION"],
    "confidence_threshold": 0.8,
    "enable_linking": true
  }'
```

#### `run_relation_extraction`
Extract relationships using GPT-4o.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/run_relation_extraction" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Preprocessed content...",
    "confidence_threshold": 0.7,
    "chunk_size": 2000
  }'
```

#### `process_file_to_ner`
Complete pipeline from file to knowledge extraction.

```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/process_file_to_ner" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/app/sunworld_test_data/sample.docx",
    "auto_detect_type": true,
    "entity_types": ["PERSON", "ORGANIZATION", "DATE"],
    "ner_confidence_threshold": 0.8,
    "enable_logging": false
  }'
```

---

### **Tool Generator Agent**

#### `generate_and_execute`
Complete dynamic tool generation workflow.

```bash
curl -X POST "http://localhost:8000/execute/Tool Generator Agent/generate_and_execute" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find the most expensive product in the dataset",
    "data": [
      {"name": "Laptop", "price": 999},
      {"name": "Phone", "price": 699},
      {"name": "Tablet", "price": 399}
    ]
  }'
```

#### `assess_complexity`
Determine query complexity for routing.

```bash
curl -X POST "http://localhost:8000/execute/Tool Generator Agent/assess_complexity" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate total sales",
    "data": [{"sales": 100}, {"sales": 200}]
  }'
```

#### `get_pending_tools`
Get tools awaiting approval.

```bash
curl -X POST "http://localhost:8000/execute/Tool Generator Agent/get_pending_tools" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### `approve_tool`
Approve a pending tool.

```bash
curl -X POST "http://localhost:8000/execute/Tool Generator Agent/approve_tool" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "tool_12345"
  }'
```

---

### **Options Pricing Agent**

#### `calculate_option_price`
Black-Scholes option pricing.

```bash
curl -X POST "http://localhost:8000/execute/Options Pricing Agent/calculate_option_price" \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "both"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "call_price": 2.13,
    "put_price": 6.04,
    "parameters": {
      "spot_price": 100,
      "strike_price": 105,
      "time_to_expiry": 0.25,
      "risk_free_rate": 0.05,
      "volatility": 0.2
    }
  }
}
```

#### `calculate_greeks`
Calculate option Greeks (delta, gamma, theta, vega, rho).

```bash
curl -X POST "http://localhost:8000/execute/Options Pricing Agent/calculate_greeks" \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call"
  }'
```

#### `calculate_implied_volatility`
Calculate implied volatility from option price.

```bash
curl -X POST "http://localhost:8000/execute/Options Pricing Agent/calculate_implied_volatility" \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "option_price": 2.13,
    "option_type": "call"
  }'
```

#### `calculate_all`
Complete option analysis (prices + Greeks).

```bash
curl -X POST "http://localhost:8000/execute/Options Pricing Agent/calculate_all" \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2
  }'
```

---

### **Meta Agent**

#### `analyze_intent`
Analyze user query intent.

```bash
curl -X POST "http://localhost:8000/execute/Meta Agent/analyze_intent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need to find information about machine learning algorithms"
  }'
```

#### `create_execution_plan`
Create multi-agent execution plan.

```bash
curl -X POST "http://localhost:8000/execute/Meta Agent/create_execution_plan" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "search",
    "context": {
      "topic": "machine learning",
      "depth": "comprehensive"
    }
  }'
```

---

### **Statistics Agent**

#### `calculate_statistics`
Calculate basic statistics.

```bash
curl -X POST "http://localhost:8000/execute/Statistics Agent/calculate_statistics" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "metrics": ["mean", "median", "std", "min", "max"]
  }'
```

#### `correlation_analysis`
Perform correlation analysis.

```bash
curl -X POST "http://localhost:8000/execute/Statistics Agent/correlation_analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "x_values": [1, 2, 3, 4, 5],
    "y_values": [2, 4, 6, 8, 10],
    "method": "pearson"
  }'
```

---

### **Vector Search Agent**

#### `semantic_search`
Semantic document search.

```bash
curl -X POST "http://localhost:8000/execute/Vector Search Agent/semantic_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "collection_id": "tech_docs",
    "limit": 10
  }'
```

#### `find_similar`
Find similar documents.

```bash
curl -X POST "http://localhost:8000/execute/Vector Search Agent/find_similar" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_12345",
    "limit": 5
  }'
```

---

## ⚠️ **Error Handling**

### **Common Error Response Format:**
```json
{
  "detail": "Error message description",
  "status_code": 400
}
```

### **Common Error Codes:**
- **400**: Bad Request (missing/invalid parameters)
- **404**: Not Found (agent or capability not found)
- **500**: Internal Server Error (processing failure)

### **Example Error Response:**
```json
{
  "detail": "Agent 'NonExistent Agent' not found",
  "status_code": 404
}
```

---

## 🚀 **Testing with cURL**

### **Basic Health Check:**
```bash
curl http://localhost:8000/health
```

### **List Available Agents:**
```bash
curl http://localhost:8000/agents | jq .
```

### **Extract Knowledge from Text:**
```bash
curl -X POST "http://localhost:8000/execute/Knowledge Graph Agent/extract_triples" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Microsoft was founded by Bill Gates and Paul Allen in Redmond, Washington.",
    "confidence_threshold": 0.8
  }' | jq .
```

### **Generate Dynamic Tool:**
```bash
curl -X POST http://localhost:8000/tool-generator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate the median of these numbers",
    "data": [5, 2, 8, 1, 9, 3, 7, 4, 6]
  }' | jq .
```

### **Option Pricing:**
```bash
curl -X POST "http://localhost:8000/execute/Options Pricing Agent/calculate_option_price" \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 150,
    "strike_price": 155,
    "time_to_expiry": 0.083,
    "risk_free_rate": 0.03,
    "volatility": 0.25
  }' | jq .
```

---

## 🔧 **Development & Testing**

### **Interactive Testing:**
1. Start the server: `docker-compose up -d`
2. Open `http://localhost:8000/docs`
3. Use the Swagger UI to test endpoints interactively
4. View request/response schemas and examples

### **Programmatic Usage:**
```python
import requests

# List agents
response = requests.get("http://localhost:8000/agents")
agents = response.json()

# Execute capability
response = requests.post(
    "http://localhost:8000/execute/Knowledge Graph Agent/extract_triples",
    json={
        "text": "Apple Inc. was founded by Steve Jobs.",
        "confidence_threshold": 0.8
    }
)
result = response.json()
```

### **Agent Name Reference:**
- `Knowledge Graph Agent`
- `Tool Generator Agent`
- `Options Pricing Agent`
- `Meta Agent`
- `Statistics Agent`
- `Vector Search Agent`

---

## 📊 **Performance Considerations**

- **Concurrent Requests**: Server handles multiple simultaneous requests
- **LLM Rate Limits**: Respect OpenAI/Claude API rate limits
- **Large Documents**: Use chunking for documents >2000 characters
- **Caching**: Results are not cached; implement if needed
- **Timeout**: LLM calls may take 5-30 seconds depending on complexity

---

**🎯 Complete API reference for building intelligent multi-agent applications!**