# Complete Setup Guide

This guide will walk you through setting up the entire MCP server and frontend from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Overview](#project-overview)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)
8. [Development Workflow](#development-workflow)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Required Software

1. **Python 3.11 or higher**
   - Check: `python3 --version`
   - Install: [python.org](https://www.python.org/downloads/)

2. **Node.js 18+ and npm**
   - Check: `node --version` and `npm --version`
   - Install: [nodejs.org](https://nodejs.org/)

3. **Ollama** (for local LLM inference)
   - Install: [ollama.ai](https://ollama.ai/)
   - After installation, pull a model:
     ```bash
     ollama pull llama3:latest
     ```
   - Verify it's running:
     ```bash
     curl http://localhost:11434/api/tags
     ```

4. **Git** (for cloning the repository)
   - Check: `git --version`

### Optional but Recommended

- **Virtual Environment** (Python venv) - included in Python 3.3+
- **Code Editor** (VS Code, Cursor, etc.)

---

## Project Overview

This project consists of:

1. **MCP Server** (Python/FastAPI backend)
   - Orchestrates multi-agent workflows
   - Uses Ollama for LLM inference
   - Runs on port 8000

2. **Frontend** (Next.js/React)
   - Simple chat interface for querying the MCP server
   - Runs on port 3000

3. **Agents**
   - **Internal Agent**: Simulates internal document retrieval
   - **External Agent**: Simulates external database queries (e.g., WIPO)

4. **Orchestrator**
   - Analyzes user queries
   - Splits queries into agent-specific tasks
   - Synthesizes results from multiple agents

---

## Step-by-Step Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd mcp-server-orchestration  # or whatever you name the repository
```

### Step 2: Set Up Python Backend

#### 2.1 Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### 2.2 Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.3 Verify Installation

```bash
python3 -c "import fastapi, uvicorn, httpx; print('✅ All dependencies installed')"
```

### Step 3: Set Up Frontend

#### 3.1 Navigate to Frontend Directory

```bash
cd frontend
```

#### 3.2 Install Node Dependencies

```bash
npm install
```

#### 3.3 Verify Installation

```bash
npm list --depth=0
```

### Step 4: Configure Environment Variables

#### 4.1 Backend Configuration

Create a `.env` file in the root directory:

```bash
cd ..  # Back to root directory
cp env.example .env
```

Edit `.env` with your settings:

```env
# Server Configuration
PORT=8000
LOG_LEVEL=INFO
ENV=development

# CORS Configuration
ALLOWED_ORIGINS=*

# Ollama Configuration (for local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

#### 4.2 Frontend Configuration

The frontend is configured to connect to `http://localhost:8000` by default. If you need to change this, edit:

```
frontend/app/api/chat/route.ts
```

Look for the `MCP_SERVER_URL` constant.

### Step 5: Verify Ollama is Running

Before starting the servers, ensure Ollama is running:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama
# On macOS: Open Ollama.app
# On Linux: ollama serve
# On Windows: ollama.exe serve
```

---

## Configuration

### Backend Configuration

The backend uses environment variables from `.env`:

- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `OLLAMA_BASE_URL`: Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: llama3:latest)

### Frontend Configuration

The frontend connects to the MCP server at `http://localhost:8000` by default.

### Agent Configuration

Agents are automatically discovered from `backend/agents/` directory. Each agent:
- Must inherit from `AgentInterface`
- Must implement required methods
- Is automatically registered on server startup

---

## Running the Application

### Option 1: Manual Start (Recommended for Development)

#### Terminal 1: Start MCP Server

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start server
python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000 --log-level info
```

The server will start on `http://localhost:8000`

#### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:3000`

### Option 2: Using Helper Scripts

#### Start MCP Server with Logs

```bash
./start_server.sh
```

This script:
- Starts the server in the background
- Shows logs in real-time
- Logs are written to `/tmp/mcp_server.log`

#### Start Frontend with MCP Server Logs

```bash
cd frontend
npm run dev
```

This will:
- Start the frontend
- Automatically show MCP server logs in the terminal

### Option 3: View Logs Separately

If servers are already running, view logs:

```bash
# View MCP server logs
tail -f /tmp/mcp_server.log
```

---

## Project Structure

```
mcp-server-orchestration/        # Project root
├── backend/                      # Backend MCP Server (Python/FastAPI)
│   ├── server/
│   │   └── mcp_server.py          # FastAPI server and endpoints
│   ├── agents/
│   │   ├── internal_agent.py      # Internal document agent
│   │   └── external_agent.py      # External database agent
│   ├── orchestrator/
│   │   └── orchestrator.py        # Query orchestration logic
│   ├── services/
│   │   └── ollama_service.py      # Ollama API wrapper
│   ├── interfaces/
│   │   └── agent.py               # Agent interface definition
│   ├── registry/
│   │   └── registry.py            # Agent registry system
│   └── discovery/
│       └── agent_discovery.py     # Automatic agent discovery
├── frontend/                      # Frontend UI (Next.js)
│   ├── app/
│   │   ├── api/
│   │   │   └── chat/
│   │   │       └── route.ts       # Chat API endpoint
│   │   ├── components/
│   │   │   └── chat.tsx           # Chat UI component
│   │   └── page.tsx               # Main page
│   └── package.json
├── requirements.txt               # Python dependencies
├── env.example                    # Environment variables template
├── start_server.sh                # Server startup script
├── view_logs.sh                   # Log viewing script
└── SETUP.md                       # This file
```

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Ollama connection errors

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
# macOS: Open Ollama.app
# Linux: ollama serve
```

### Issue: Port already in use

**Solution:**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or for port 3000
kill -9 $(lsof -ti:3000)
```

### Issue: Frontend can't connect to backend

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `.env`
3. Verify frontend is pointing to correct URL in `frontend/app/api/chat/route.ts`

### Issue: Agents not being discovered

**Solution:**
1. Ensure agents are in `backend/agents/` directory
2. Check that agents inherit from `AgentInterface`
3. Verify `__init__.py` files exist in agent directories
4. Check server logs for discovery errors

### Issue: Slow responses

**Solution:**
- This is normal with local Ollama - responses take 10-60 seconds
- Consider using a faster model or GPU acceleration
- Check Ollama logs for performance issues

### Issue: JSON parsing errors

**Solution:**
- The system has fallback JSON parsing
- If errors persist, check Ollama model output
- Consider using a different model or adjusting prompts

---

## Development Workflow

### Making Changes to Agents

1. Edit agent files in `backend/agents/`
2. Restart the MCP server
3. Agents are automatically re-discovered

### Making Changes to Frontend

1. Edit files in `frontend/app/`
2. Frontend auto-reloads (hot reload)
3. No restart needed

### Viewing Logs

All MCP server logs are written to `/tmp/mcp_server.log`

View in real-time:
```bash
tail -f /tmp/mcp_server.log
```

### Testing the System

1. Start both servers (backend + frontend)
2. Open `http://localhost:3000` in browser
3. Try a query like: "can you tell me from my italy-xxx contract what i need to change for it to work in australia"
4. Check logs to see the workflow execution

---

## Workflow Explanation

When a user submits a query:

1. **Query Reception**: Frontend sends query to `/orchestrate` endpoint
2. **Query Analysis**: Orchestrator uses Ollama to:
   - Determine which agents are needed
   - Generate optimized queries for each agent
3. **Agent Execution**: 
   - Agents execute in sequence (can be parallelized)
   - Each agent uses Ollama to generate responses
4. **Result Synthesis**: Orchestrator:
   - Compares results from all agents
   - Synthesizes a comprehensive answer
5. **Response**: Final answer returned to frontend

### Example Query Flow

**User Query**: "can you tell me from my italy-xxx contract what i need to change for it to work in australia"

**Step 1 - Analysis**:
- Determines: Both `internal_agent` and `external_agent` needed
- Generates queries:
  - Internal: "Find italy-xxx contract terms and setup procedures"
  - External: "Find Australian compliance standards and regional requirements"

**Step 2 - Execution**:
- Internal agent returns contract information (908 chars)
- External agent returns compliance requirements (1732 chars)

**Step 3 - Synthesis**:
- Orchestrator compares both results
- Generates comprehensive answer (2421 chars)
- Returns to user

---

## Environment Variables Reference

### Backend (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENV` | `development` | Environment (development, production) |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3:latest` | Default Ollama model |

---

## API Endpoints

### MCP Server (Port 8000)

- `GET /health` - Health check
- `POST /orchestrate` - Process user query
  ```json
  {
    "query": "your query here"
  }
  ```
- `GET /mcp/agents` - List available agents
- `POST /discover` - Discover agents

### Frontend (Port 3000)

- `GET /` - Main chat interface
- `POST /api/chat` - Chat endpoint (forwards to MCP server)

---

## Next Steps

After setup:

1. **Test the system** with sample queries
2. **Customize agents** for your specific use case
3. **Adjust prompts** in agent files and orchestrator
4. **Add new agents** by creating files in `backend/agents/`
5. **Modify frontend** UI in `frontend/app/`

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review server logs: `/tmp/mcp_server.log`
3. Check Ollama is running: `curl http://localhost:11434/api/tags`
4. Verify all dependencies are installed

---

## License

[Add your license information here]

---

**Last Updated**: November 2024

