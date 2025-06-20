# Samvid MCP Server

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

A standalone HTTP API server for Samvid's Model Context Protocol (MCP) agents.

## Overview

This server provides REST endpoints for the main Samvid application to communicate with MCP agents. It's designed to run independently from the main Next.js application, making it compatible with Vercel's serverless deployment.

## Features

- **Agent Discovery**: Find available agents and their capabilities
- **Tool Discovery**: Discover tools provided by agents
- **Agent Invocation**: Execute agents with input data
- **Tool Invocation**: Execute specific tools
- **Session Management**: Create, update, and manage user sessions
- **Health Monitoring**: Health check endpoint for monitoring

## 🐳 Quick Start with Docker (Recommended)

### Option 1: Docker Compose (Full Setup with Database)

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
   - PostgreSQL database on port `5432`

3. **Verify it's running:**
   ```bash
   curl http://localhost:8000/health
   ```

### Option 2: Docker Only (Standalone)

1. **Clone and build:**
   ```bash
   git clone https://github.com/samvid-ai/samvid-mcp-server.git
   cd samvid-mcp-server
   docker build -t samvid-mcp-server .
   ```

2. **Run the container:**
   ```bash
   docker run -d --name samvid-mcp-server -p 8000:8000 samvid-mcp-server
   ```

3. **Test the API:**
   ```bash
   curl http://localhost:8000/health
   ```

### Option 3: Pre-built Image (Coming Soon)

```bash
# Pull and run the pre-built image
docker run -d --name samvid-mcp-server -p 8000:8000 samvidai/mcp-server:0.1.0
```

## 🚀 Manual Installation

### Prerequisites

- Python 3.11+ (tested with Python 3.13)
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

**Development mode:**
```bash
python -m src.server
```

**Production mode:**
```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

## 📋 API Endpoints

### Health Check
- `GET /health` - Server health status

### Agent Management
- `POST /agents/discover` - Discover available agents
- `POST /agents/invoke` - Invoke an agent

### Tool Management
- `POST /tools/discover` - Discover available tools
- `POST /tools/invoke` - Invoke a specific tool

### Session Management
- `POST /sessions/create` - Create a new session
- `GET /sessions/{session_id}` - Get session details
- `PUT /sessions/{session_id}` - Update session
- `DELETE /sessions/{session_id}` - Terminate session

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

## 🔧 Configuration

Environment variables:

- `PORT` - Server port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ALLOWED_ORIGINS` - CORS allowed origins (default: http://localhost:3000)
- `DATABASE_URL` - PostgreSQL connection string (optional)
- `NODE_ENV` - Environment mode (development/production)

## 🧪 Testing the API

### Basic Health Check
```bash
curl http://localhost:8000/health
```

### Discover Available Agents
```bash
curl -X POST http://localhost:8000/agents/discover \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Invoke an Agent
```bash
curl -X POST http://localhost:8000/agents/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "knowledge_graph",
    "input_data": {"entity": "Python"},
    "context": {"depth": 2}
  }'
```

### Create a Session
```bash
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "context": {"test": "data"}
  }'
```

## 🛠️ Development

### Current Implementation

The server currently includes these agents:
- **MetaAgent** - Orchestration agent for managing other agents
- **VectorSearchAgent** - Semantic search capabilities
- **KnowledgeGraphAgent** - Knowledge graph traversal and analysis
- **StatsAgent** - Analytics and statistics

### Docker Commands for Development

```bash
# View logs
docker-compose logs -f mcp-server

# Access container shell
docker-compose exec mcp-server bash

# Rebuild after changes
docker-compose up -d --build

# Stop all services
docker-compose down

# Clean up
docker-compose down -v  # Removes volumes too
```

### Adding Real Agents

To replace mock agents with real implementations:

1. Create agent classes in `src/agents/`
2. Implement the required methods:
   - `get_agent_info()`
   - `get_tools()`
   - `execute(input_data, context)`
   - `execute_tool(tool_name, arguments)`
3. Update the agent initialization in `src/server.py`

## ��️ Architecture

```