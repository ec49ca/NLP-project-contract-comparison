# MCP Server with Multi-Agent Orchestration

A Model Context Protocol (MCP) server with multi-agent orchestration capabilities, featuring a simple web interface for querying agents. This system uses local Ollama for LLM inference and orchestrates multiple agents to process complex queries.

## Features

- **MCP-Compliant**: Implements Model Context Protocol standards
- **FastAPI Server**: Modern async Python web framework
- **Multi-Agent Orchestration**: Intelligent query splitting and result synthesis
- **Local LLM Support**: Uses Ollama for local LLM inference
- **Web Interface**: Simple Next.js frontend for querying the server
- **Automatic Agent Discovery**: Agents are automatically discovered and registered
- **RESTful API**: Standard HTTP endpoints for agent management

## Quick Start

**For detailed setup instructions, see [SETUP.md](./SETUP.md)**

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running
- Model pulled: `ollama pull llama3:latest`

### Quick Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd agentforge

# 2. Set up Python backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up frontend
cd agenthub-main
npm install
cd ..

# 4. Configure environment
cp env.example .env
# Edit .env with your settings

# 5. Start Ollama (if not running)
# macOS: Open Ollama.app
# Linux: ollama serve

# 6. Start servers
# Terminal 1: MCP Server
source venv/bin/activate
python3 -m uvicorn src.server.mcp_server:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd agenthub-main
npm run dev
```

Access the frontend at `http://localhost:3000`

## Architecture

### Components

1. **MCP Server** (Python/FastAPI)
   - Orchestrates multi-agent workflows
   - Uses Ollama for LLM inference
   - Runs on port 8000

2. **Frontend** (Next.js/React)
   - Simple chat interface
   - Connects to MCP server
   - Runs on port 3000

3. **Agents**
   - **Internal Agent**: Simulates internal document retrieval
   - **External Agent**: Simulates external database queries

4. **Orchestrator**
   - Analyzes user queries using LLM
   - Splits queries into agent-specific tasks
   - Synthesizes results from multiple agents

### Workflow

```
User Query → Orchestrator → Query Analysis (LLM)
                              ↓
                    Determine Agents Needed
                              ↓
                    Generate Optimized Queries
                              ↓
                    Execute Agents (Parallel)
                              ↓
                    Compare & Synthesize Results (LLM)
                              ↓
                    Return Final Answer
```

## API Endpoints

### MCP Server (Port 8000)

- `GET /health` - Health check
- `POST /orchestrate` - Process user query
  ```json
  {
    "query": "your query here"
  }
  ```
- `GET /mcp/agents` - List all registered agents
- `GET /mcp/resources` - List all MCP resources
- `POST /discover` - Trigger agent discovery

### Frontend (Port 3000)

- `GET /` - Main chat interface
- `POST /api/chat` - Chat endpoint (forwards to MCP server)

## Project Structure

```
agentforge/
├── src/
│   ├── server/
│   │   └── mcp_server.py          # FastAPI server
│   ├── agents/
│   │   ├── internal_agent.py      # Internal document agent
│   │   └── external_agent.py      # External database agent
│   ├── orchestrator/
│   │   └── orchestrator.py        # Query orchestration
│   ├── services/
│   │   └── ollama_service.py      # Ollama API wrapper
│   ├── interfaces/
│   │   └── agent.py               # Agent interface
│   ├── registry/
│   │   └── registry.py            # Agent registry
│   └── discovery/
│       └── agent_discovery.py     # Auto-discovery
├── agenthub-main/                 # Frontend
│   ├── app/
│   │   ├── api/chat/route.ts      # Chat API
│   │   └── components/chat.tsx    # Chat UI
│   └── package.json
├── requirements.txt               # Python dependencies
├── env.example                    # Environment template
├── SETUP.md                       # Detailed setup guide
└── README.md                      # This file
```

## Configuration

Create a `.env` file from `env.example`:

```env
PORT=8000
LOG_LEVEL=INFO
ENV=development
ALLOWED_ORIGINS=*
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

## Documentation

- **[SETUP.md](./SETUP.md)** - Comprehensive setup guide with step-by-step instructions
- **[QUICKSTART.md](./QUICKSTART.md)** - Quick start guide (if exists)

## Development

### Running Tests

```bash
pytest
```

### Viewing Logs

MCP server logs are written to `/tmp/mcp_server.log`:

```bash
tail -f /tmp/mcp_server.log
```

### Helper Scripts

- `./start_server.sh` - Start MCP server with log viewing
- `./view_logs.sh` - View MCP server logs

## Troubleshooting

See [SETUP.md](./SETUP.md#troubleshooting) for detailed troubleshooting guide.

Common issues:
- **Ollama not running**: Start Ollama and verify with `curl http://localhost:11434/api/tags`
- **Port conflicts**: Kill processes on ports 8000 or 3000
- **Module not found**: Ensure virtual environment is activated and dependencies installed

## License

[Add your license information here]

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request
