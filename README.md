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

## 🧑‍💻 How to Create a New Agent

1. **Create a new file** in `src/agents/` (e.g., `my_agent.py`).
2. **Subclass `AgentInterface`** from `src/interfaces/agent.py`.
3. **Implement all required properties and methods:**
   - `name` (property): Human-readable name
   - `description` (property): Short description
   - `agent_id_str` (property): Unique, stable string identifier (e.g., "my_agent")
   - `uuid` (property + setter): Will be set by the registry
   - `initialize(config)` (async): Any setup logic
   - `process_request(request)` (async): Main entrypoint for handling requests
   - `get_capabilities()` (returns dict): Describe what the agent can do
   - `get_status()` (returns dict): Health/status info
   - `shutdown()` (async): Cleanup logic
4. **Expose capabilities** in `get_capabilities()` as a dictionary, e.g.:
   ```python
   def get_capabilities(self) -> Dict[str, Any]:
       return {
           "my_capability": {
               "description": "What this does",
               "parameters": {"param1": "desc", ...}
           },
           ...
       }
   ```
5. **Implement `process_request()`** to handle commands/capabilities, e.g.:
   ```python
   async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
       command = request.get("command")
       if command == "my_capability":
           return await self._my_capability(request)
       ...
   ```
6. **(Optional) Add tools** in `src/agents/tools/` if your agent needs reusable logic.
7. **Test your agent:**
   - It will be auto-discovered and registered on server startup.
   - Use `/agents`, `/mcp/resources`, and `/primitives/{primitive_name}` to verify.
8. **Update routing:**
   - Use the `/routes/{primitive_name}` endpoint to map new primitives to your agent.
   - Example:
     ```bash
     curl -X POST http://localhost:8000/routes/my_capability \
       -H "Content-Type: application/json" \
       -d '{"agent_id": "<your-agent-uuid>"}'
     ```
9. **Document your agent and capabilities** in the code and in the project documentation.

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
- Follow the agent interface and registration patterns described above.
- When adding a new agent, implement the `AgentInterface` and define a unique `agent_id_str`.
- Update documentation and add tests for new features.
- Keep code modular, readable, and maintainable.

---

For a full architecture and onboarding guide, see `ARCHITECTURE.md`.
