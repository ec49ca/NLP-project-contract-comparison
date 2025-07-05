# Samvid MCP Server

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

A standalone HTTP API server for Samvid's Model Context Protocol (MCP) agents.

---

## Overview

This server provides REST endpoints for the main Samvid application to communicate with MCP agents. It is designed for modularity, extensibility, and ease of integration.

---

## 🐳 Quick Start with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/samvid-ai/samvid-mcp-server.git
   cd samvid-mcp-server
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```
   This will start:
   - Samvid MCP Server on `http://localhost:8000`
   - Neo4j (and optionally PostgreSQL) for agent storage

3. **Verify it's running:**
   ```bash
   curl http://localhost:8000/health
   ```

---

## 📋 API Endpoints

### Health & Discovery
- `GET /health` — Server health status
- `POST /discover` — Auto-discover and register all available agents

### Agent Management
- `POST /agents` — Register a new agent (by class name and config)
- `GET /agents` — List all registered agents
- `GET /agents/{agent_id}` — Get info about a specific agent

### Routing
- `POST /routes/{primitive_name}` — Register a route (primitive → agent)
- `DELETE /routes/{primitive_name}` — Unregister a route
- `GET /routes` — List all registered routes

### Primitive Invocation
- `POST /primitives/{primitive_name}` — Route a request to the agent responsible for a primitive

### Resource Discovery
- `GET /mcp/resources` — List all available MCP resources (agents and their capabilities)

### API Documentation
- Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

---

## 🧑‍💻 Creating New Agents

### Quick Start
Creating a new agent is now streamlined with our template system:

1. **Copy the template:**
   ```bash
   cp src/agents/template_agent.py src/agents/your_agent_name_agent.py
   ```

2. **Follow the customization guide:**
   - See [`AGENT_DEVELOPMENT_GUIDE.md`](./AGENT_DEVELOPMENT_GUIDE.md) for detailed instructions
   - The template includes all required standardized attributes and methods
   - Clear comments guide you through each customization step

3. **Register your agent:**
   ```python
   # Add to src/agents/__init__.py
   from .your_agent_name_agent import YourAgentNameAgent
   ```

4. **Test and deploy:**
   - Your agent will be auto-discovered on server startup
   - Use the API endpoints to verify functionality

### Agent Standards
All agents in the system follow these standards:
- **Tab indentation** for consistency
- **Standard attributes**: `agent_id`, `category`, `status`, `_tools`
- **Error handling patterns** with consistent response formats
- **Comprehensive logging** and documentation
- **Async/await patterns** for I/O operations

### Available Agent Categories
- `analysis` — Data analysis and statistical operations
- `search` — Search and retrieval operations
- `financial_modeling` — Financial calculations and modeling
- `knowledge_management` — Knowledge graphs and information extraction
- `tool_generation` — Dynamic tool creation
- `communication` — External API integrations
- `data_processing` — Data transformation and processing
- `machine_learning` — ML model training and inference

### Current Agents
- **Knowledge Graph Agent** (`knowledge_management`) — Triple extraction and graph operations
- **Meta Agent** (`analysis`) — Intent analysis and execution planning
- **Options Agent** (`financial_modeling`) — Black-Scholes option pricing
- **Statistics Agent** (`analysis`) — Statistical analysis and modeling
- **Tool Generator Agent** (`tool_generation`) — Dynamic tool creation
- **Vector Search Agent** (`search`) — Semantic document search

For detailed development instructions, examples, and best practices, see the [**Agent Development Guide**](./AGENT_DEVELOPMENT_GUIDE.md).

---

## 🔧 Configuration

Environment variables:
- `PORT` — Server port (default: 8000)
- `LOG_LEVEL` — Logging level (default: INFO)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — Neo4j connection (for KG agent)
- `OPENAI_API_KEY` — OpenAI API key (for NLP tools)
- See `env.example` for more

---

## 🛠️ Development & Manual Installation

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation Steps
1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

### Running the Server
- **Development:**
  ```bash
  python -m src.server
  ```
- **Production:**
  ```bash
  uvicorn src.server:app --host 0.0.0.0 --port 8000
  ```

---

## 🤝 Contributing

### Agent Development
- Use the provided `template_agent.py` as your starting point
- Follow the [Agent Development Guide](./AGENT_DEVELOPMENT_GUIDE.md) for best practices
- All agents must implement the `AgentInterface` with standardized attributes
- Include comprehensive tests and documentation

### Code Standards
- **Indentation**: Use tabs (converted from spaces during standardization)
- **Naming**: Follow Python conventions (snake_case for files, PascalCase for classes)
- **Error handling**: Use consistent error response formats
- **Documentation**: Include docstrings and inline comments

### Testing
- Write unit tests for new agents
- Test API endpoints with realistic scenarios
- Verify agent discovery and registration
- Check error handling and edge cases

---

## 📚 Documentation

- **[Agent Development Guide](./AGENT_DEVELOPMENT_GUIDE.md)** — Complete guide for creating new agents
- **[Architecture Guide](./ARCHITECTURE.md)** — System architecture and design patterns
- **[API Documentation](http://localhost:8000/docs)** — Interactive API documentation (when server is running)

---

For a full architecture and onboarding guide, see `ARCHITECTURE.md`.
