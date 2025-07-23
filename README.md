# Samvid MCP Server

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
![Neo4j](https://img.shields.io/badge/neo4j-5.19+-orange.svg)

A multi-agent HTTP API server implementing the Model Context Protocol (MCP) with flexible LLM provider support and specialized agents for knowledge extraction, financial modeling, and dynamic tool generation.

---

## 🚀 **Key Features**

- **🤖 Multi-Agent System**: 6 specialized agents for different domains
- **🔄 LLM Provider Hotswapping**: Support for OpenAI, Claude, and Grok with runtime switching
- **📊 Knowledge Graph**: Advanced triple extraction with Neo4j integration
- **⚙️ Dynamic Tool Generation**: Create custom tools from natural language
- **📈 Financial Modeling**: Black-Scholes option pricing and Greeks calculation
- **🔍 Document Processing**: OCR, NER+EL, and relationship extraction
- **🐳 Docker Ready**: Full containerization with docker-compose

---

## 🐳 **Quick Start with Docker**

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd samvid-mcp
   cp env.example .env
   # Edit .env with your API keys
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```
   This starts:
   - **MCP Server** on `http://localhost:8000`
   - **Neo4j** on `http://localhost:7474` (if enabled)

3. **Verify running:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **View interactive docs:**
   Open `http://localhost:8000/docs` for Swagger UI

---

## 🤖 **Available Agents**

### **1. Knowledge Graph Agent** (`knowledge_management`)
Extract knowledge from documents and build graph relationships.

**Capabilities:**
- `extract_triples` - Extract subject-predicate-object relationships from text
- `detect_document_type` - Classify document structure (7-point scale)
- `preprocess_document` - Clean and normalize documents with OCR support
- `run_ner_el` - Named Entity Recognition + Entity Linking using GPT-4
- `run_relation_extraction` - Extract relationships using GPT-4o
- `process_file_to_ner` - Complete pipeline from file to knowledge graph

### **2. Tool Generator Agent** (`tool_generation`)
Generate dynamic tools from natural language queries.

**Capabilities:**
- `generate_and_execute` - Complete workflow with complexity assessment
- `assess_complexity` - Determine if query is simple or complex
- `generate_direct` - Quick generation for simple queries
- `analyze_and_plan` - Plan complex multi-step solutions
- `get_pending_tools` / `approve_tool` - Tool approval workflow

### **3. Options Agent** (`financial_modeling`)
Black-Scholes option pricing and risk calculations.

**Capabilities:**
- `calculate_option_price` - Call/put option prices
- `calculate_greeks` - Delta, gamma, theta, vega, rho
- `calculate_implied_volatility` - Reverse-engineer volatility
- `calculate_all` - Complete option analysis

### **4. Meta Agent** (`analysis`)
Intent analysis and execution planning coordinator.

**Capabilities:**
- `analyze_intent` - Determine user intent from queries
- `create_execution_plan` - Multi-agent coordination plans

### **5. Statistics Agent** (`analysis`)
Statistical analysis and data processing.

**Capabilities:**
- `calculate_statistics` - Mean, median, std dev, etc.
- `correlation_analysis` - Correlation between variables

### **6. Vector Search Agent** (`search`)
Semantic document search (placeholder implementation).

**Capabilities:**
- `semantic_search` - Semantic document search
- `find_similar` - Find similar documents

---

## 🔄 **LLM Provider System**

Flexible multi-provider LLM system with runtime switching:

### **Supported Providers:**
- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- **Claude**: Claude-3-5-sonnet, Claude-3-haiku
- **Grok**: (Ready for future integration)

### **Configuration:**
```bash
# .env
DEFAULT_LLM_MODEL=openai:gpt-4o
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
```

### **Usage Examples:**
```python
# Use global default
await llm_service.simple_completion("Hello")

# Override provider
await llm_service.simple_completion("Complex analysis", provider="claude")

# Override model for cost optimization
await llm_service.simple_completion("Simple task", model="gpt-4o-mini")
```

See **[LLM_SERVICE_GUIDE.md](./LLM_SERVICE_GUIDE.md)** for complete usage guide.

---

## 📡 **API Endpoints**

### **Core Endpoints:**
- `GET /health` — Server health and stats
- `GET /docs` — Interactive API documentation
- `POST /agents` — Register new agent instances
- `GET /agents` — List all registered agents
- `GET /agents/{agent_id}` — Get specific agent info

### **Agent Execution:**
- `POST /execute/{agent_name}/{capability}` — Execute agent capability
- `POST /tool-generator/execute` — Convenience endpoint for tool generation

### **Resource Discovery:**
- `GET /mcp/resources` — List all available MCP resources
- `POST /discover` — Auto-discover and register agents

See **[API_ENDPOINTS_GUIDE.md](./API_ENDPOINTS_GUIDE.md)** for detailed documentation with examples.

---

## ⚙️ **Configuration**

### **Required Environment Variables:**
```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=openai:gpt-4o

# Neo4j (for Knowledge Graph Agent)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Server Configuration
PORT=8000
LOG_LEVEL=INFO
```

### **Optional Variables:**
```bash
# Additional LLM Providers
CLAUDE_API_KEY=sk-ant-...
GROK_API_KEY=... # When available

# Database (if using external)
DATABASE_URL=postgresql://...
```

---

## 🛠️ **Development**

### **Manual Installation:**
```bash
# Python 3.11+ required
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your configuration
python -m src.server.mcp_server
```

### **Creating New Agents:**
1. **Copy template:**
   ```bash
   cp src/agents/template_agent.py src/agents/my_agent.py
   ```

2. **Customize the template:**
   - Update `_agent_id_str`, `_name`, `_description`
   - Set appropriate `category`
   - Implement `process_request()` logic
   - Define `get_capabilities()`

3. **Register agent:**
   ```python
   # Add to src/agents/__init__.py
   from .my_agent import MyAgent
   __all__ = [..., "MyAgent"]
   ```

4. **Auto-discovery:**
   - Agents are automatically discovered on server startup
   - No manual registration required

### **Agent Categories:**
- `knowledge_management` — Knowledge extraction and graphs
- `financial_modeling` — Financial calculations and modeling
- `tool_generation` — Dynamic tool creation
- `analysis` — Data analysis and statistics
- `search` — Search and retrieval
- `communication` — External API integrations
- `data_processing` — Data transformation

---

## 🏗️ **Architecture**

```
samvid-mcp/
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── tools/       # Agent-specific tools
│   │   └── *.py         # Individual agents
│   ├── interfaces/      # Abstract interfaces
│   ├── providers/       # LLM provider implementations
│   ├── services/        # Core services (LLM, Neo4j, config)
│   ├── registry/        # Agent registration system
│   ├── discovery/       # Auto-discovery system
│   └── server/          # FastAPI server
├── docker-compose.yml   # Container orchestration
├── Dockerfile          # Container definition
└── requirements.txt    # Python dependencies
```

### **Key Components:**
- **FastAPI Server**: HTTP API with auto-generated docs
- **Agent Registry**: Manages agent lifecycle and routing
- **LLM Service**: Multi-provider LLM abstraction layer
- **Neo4j Service**: Graph database for knowledge graphs
- **Discovery System**: Auto-finds and registers agents

---

## 🧪 **Testing**

### **Test Suite Status**
**✅ 113 tests passing** | **⚠️ 19 tests skipped** (import conflicts)

The project includes a comprehensive test suite covering all major components:

```bash
# Run all tests
./test

# Run specific categories
./test agents      # Agent tests (47 tests)
./test services    # Service layer tests (28 tests)
./test registry    # Registry system tests (15 tests)
./test tools       # Agent tools tests (13 tests)
./test config      # Configuration tests (12 tests)
./test server      # Server endpoint tests (12 tests)
```

### **Test Coverage**
- **🧠 Agents**: Knowledge Graph Agent, Tool Generator Agent (47 tests)
- **📝 Registry**: Agent registration and management (15 tests)
- **🔧 Services**: LLM service, prompt service (28 tests)
- **🛠️ Tools**: Document detection, triple extraction (13 tests)
- **⚙️ Config**: Configuration management (12 tests)
- **🌐 Server**: API endpoints and error handling (12 tests)

### **Basic API Testing:**
```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/agents

# Execute capability
curl -X POST http://localhost:8000/execute/Knowledge\ Graph\ Agent/extract_triples \
  -H "Content-Type: application/json" \
  -d '{"text": "John works at OpenAI in San Francisco"}'
```

### **Interactive Testing:**
- Open `http://localhost:8000/docs` for Swagger UI
- Test all endpoints with built-in forms
- View request/response schemas

### **Test Documentation**
See [tests/README.md](./tests/README.md) for detailed test documentation, including:
- Test categories and coverage
- Known issues and workarounds
- Development testing guidelines
- CI/CD integration

---

## 🐳 **Docker Configuration**

### **Services:**
- **mcp-server**: Main application (port 8000)
- **neo4j**: Graph database (ports 7474, 7687) [optional]
- **db**: PostgreSQL database [optional]

### **Volumes:**
- `./generated_tools:/app/generated_tools` — Dynamic tool storage
- `./logs:/app/logs` — Application logs
- `./sunworld_test_data:/app/sunworld_test_data` — Test documents

### **Networks:**
- `mcp-network`: Internal Docker network for service communication

---

## 📚 **Documentation**

- **[API_ENDPOINTS_GUIDE.md](./API_ENDPOINTS_GUIDE.md)** — Complete API reference
- **[LLM_SERVICE_GUIDE.md](./LLM_SERVICE_GUIDE.md)** — LLM provider usage guide
- **[AGENT_DEVELOPMENT_GUIDE.md](./AGENT_DEVELOPMENT_GUIDE.md)** — Agent development guide
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — System architecture overview

---

## 🤝 **Contributing**

### **Development Workflow:**
1. Create feature branch
2. Follow coding standards (tabs, consistent naming)
3. Implement comprehensive error handling
4. Add logging and documentation
5. Test with multiple agents
6. Submit pull request

### **Code Standards:**
- **Python 3.11+** with type hints
- **Tab indentation** for consistency
- **Async/await** for I/O operations
- **Comprehensive logging** with structured messages
- **Error handling** with user-friendly messages

---

## 📄 **License**

See [LICENSE](./LICENSE) for details.

---

## 🚀 **Quick Examples**

### **Extract Knowledge from Text:**
```bash
curl -X POST http://localhost:8000/execute/Knowledge\ Graph\ Agent/extract_triples \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Inc. was founded by Steve Jobs in Cupertino, California.",
    "confidence_threshold": 0.8
  }'
```

### **Generate Dynamic Tool:**
```bash
curl -X POST http://localhost:8000/tool-generator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate average of numbers",
    "data": [1, 2, 3, 4, 5]
  }'
```

### **Option Pricing:**
```bash
curl -X POST http://localhost:8000/execute/Options\ Pricing\ Agent/calculate_option_price \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2
  }'
```

**🎯 Ready to build intelligent multi-agent systems with flexible LLM providers!**
