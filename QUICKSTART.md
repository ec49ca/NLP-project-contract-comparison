# Quick Start Guide

## Prerequisites

1. **Ollama is running** (should already be running on your system)
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # If not running, start it:
   ollama serve
   ```

2. **Python 3.11+** with virtual environment
3. **Node.js** for the frontend

## Setup Steps

### 1. Backend (MCP Server)

```bash
# Navigate to project root
cd /path/to/mcp-server-orchestration  # Update with your actual path

# Activate virtual environment (already created)
source venv/bin/activate

# Install dependencies (already done, but if needed):
pip install -r requirements.txt

# Start the MCP server
python3 -m uvicorn backend.server.mcp_server:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script:
./start_server.sh
```

The server will start on `http://localhost:8000`

### 2. Frontend (Next.js UI)

```bash
# In a new terminal, navigate to frontend
cd /path/to/mcp-server-orchestration  # Update with your actual path/frontend

# Install dependencies (already done, but if needed):
npm install

# Start the frontend
npm run dev
```

The frontend will start on `http://localhost:3000`

## Testing

1. Open `http://localhost:3000` in your browser
2. Type a query like: "What are the contract terms in Italy?"
3. The query will go: Frontend → MCP Server Orchestrator → Agents → Response

## Verify Everything is Working

### Test MCP Server directly:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/mcp/agents
```

### Test Orchestrator:
```bash
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the contract terms in Italy?"}'
```

## Troubleshooting

- **Ollama not responding**: Make sure `ollama serve` is running
- **Port 8000 in use**: Change PORT in `.env` file
- **Port 3000 in use**: Next.js will automatically use the next available port
- **Import errors**: Make sure virtual environment is activated and dependencies are installed

