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

3. **Ollama** (for local LLM inference, optional)
   - Install: [ollama.ai](https://ollama.ai/)
   - After installation, pull a model:
     ```bash
     ollama pull llama3:latest
     ```
   - Verify it's running:
     ```bash
     curl http://localhost:11434/api/tags
     ```

4. **Pinecone Account** (for external agent - WIPO document search)
   - Sign up at [pinecone.io](https://www.pinecone.io/)
   - Get your API key from the dashboard
   - Create an index (the script will create it automatically if it doesn't exist)

5. **OpenAI Account** (required for external agent embeddings)
   - Get API key from [platform.openai.com](https://platform.openai.com/)
   - Even if you use a different LLM provider for queries, OpenAI is needed for generating embeddings

6. **Git** (for cloning the repository)
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
   - **Internal Agent**: Searches through uploaded PDF documents using extracted text, extracts structured quotes
   - **External Agent**: Queries WIPO compliance databases using Pinecone vector search, returns structured chunks with source information

4. **Orchestrator**
   - Analyzes user queries using LLM
   - Automatically detects and matches documents from query text
   - Splits queries into agent-specific tasks
   - Synthesizes results from multiple agents
   - Has access to all uploaded documents for intelligent routing

5. **Document Management**
   - PDF upload with automatic text extraction (pdfplumber)
   - Document storage (filesystem + in-memory cache)
   - Manual document selection via UI
   - Automatic document detection from queries
   - WIPO document processing and Pinecone upload for external agent

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
python3 -c "import fastapi, uvicorn, httpx, pdfplumber, pinecone, openai, PyPDF2, tiktoken; print('✅ All dependencies installed')"
```

This verifies that all required packages including `pdfplumber`, `pinecone`, `openai`, `PyPDF2`, and `tiktoken` are installed correctly.

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

Edit `.env` with your settings. **Choose ONE provider to start with:**

**For Ollama (Local, Free):**
```env
# Server Configuration
PORT=8000
LOG_LEVEL=INFO
ENV=development

# CORS Configuration
ALLOWED_ORIGINS=*

# LLM Provider Configuration
LLM_PROVIDER=ollama

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
# Optional: Add more models for dropdown
# OLLAMA_MODELS=llama3:latest,llama3.1:latest,mistral:latest
```

**For OpenAI (Cloud, Paid):**
```env
# Server Configuration
PORT=8000
LOG_LEVEL=INFO
ENV=development

# CORS Configuration
ALLOWED_ORIGINS=*

# LLM Provider Configuration
LLM_PROVIDER=openai

# OpenAI Configuration (Required for queries AND external agent embeddings)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
# Optional: Add more models for dropdown
# OPENAI_MODELS=gpt-4o,gpt-4-turbo,gpt-4,gpt-3.5-turbo

# Pinecone Configuration (Required for external agent)
PINECONE_API_KEY=your-pinecone-api-key-here
```

**Note**: 
- You can configure multiple providers in `.env`. The UI will show all configured providers, and you can switch between them. See `env.example` for all options.
- **Pinecone and OpenAI are required** for the external agent to work. Even if you use a different LLM provider for queries, you still need OpenAI for generating embeddings.

#### 4.2 Frontend Configuration

The frontend is configured to connect to `http://localhost:8000` by default. If you need to change this, edit:

```
frontend/app/api/chat/route.ts
```

Look for the `MCP_SERVER_URL` constant.

### Step 5: Set Up Pinecone and WIPO Documents (Required for External Agent)

The external agent requires Pinecone for vector search and WIPO documents to be processed:

1. **Place WIPO PDFs in the correct directory:**
   ```bash
   # Create directory if it doesn't exist
   mkdir -p backend/uploads/wipo_documents
   
   # Place your WIPO PDF files in this directory
   # Example: wipo_pub_903.pdf, wipo_pub_868.pdf, etc.
   ```

2. **Process WIPO documents and upload to Pinecone:**
   ```bash
   # Make sure you're in the project root and venv is activated
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Run the data extraction script
   python3 -m backend.data_extraction
   ```

   This script will:
   - Read all PDFs from `backend/uploads/wipo_documents/`
   - Extract text using PyPDF2
   - Chunk text using tiktoken (token-based chunking)
   - Generate OpenAI embeddings
   - Create Pinecone index if it doesn't exist
   - Upload all chunks to Pinecone

3. **Verify setup:**
   - Check that `.env` has `PINECONE_API_KEY` and `OPENAI_API_KEY` set
   - The script will print success messages when chunks are uploaded

### Step 6: Verify Your LLM Provider is Ready

Before starting the servers, ensure your selected LLM provider is configured:

**If using Ollama:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama
# On macOS: Open Ollama.app
# On Linux: ollama serve
# On Windows: ollama.exe serve
```

**If using OpenAI/Anthropic/Google:**
- Ensure your API key is set in `.env`
- No additional setup needed - the system will connect to their APIs

**Important**: Even if you use Ollama/Anthropic/Google for queries, you still need OpenAI API key in `.env` for the external agent to generate embeddings.

---

## Configuration

### Backend Configuration

The backend uses environment variables from `.env`:

**Server Settings:**
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENV`: Environment (development, production)
- `ALLOWED_ORIGINS`: CORS allowed origins (default: *)

**LLM Provider Settings:**
- `LLM_PROVIDER`: Default provider - `ollama`, `openai`, `anthropic`, or `google` (default: ollama)

**Ollama Settings (when LLM_PROVIDER=ollama):**
- `OLLAMA_BASE_URL`: Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Default model (default: llama3:latest)
- `OLLAMA_MODELS`: Comma-separated list of models for dropdown (optional)

**OpenAI Settings (when LLM_PROVIDER=openai):**
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Default model (default: gpt-4)
- `OPENAI_MODELS`: Comma-separated list of models for dropdown (optional)
- `OPENAI_BASE_URL`: API base URL (optional, defaults to OpenAI)

**Anthropic Settings (when LLM_PROVIDER=anthropic):**
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `ANTHROPIC_MODEL`: Default model (default: claude-3-5-sonnet-20241022)
- `ANTHROPIC_MODELS`: Comma-separated list of models for dropdown (optional)

**Google Settings (when LLM_PROVIDER=google):**
- `GOOGLE_API_KEY`: Your Google API key (required)
- `GOOGLE_MODEL`: Default model (default: gemini-pro)
- `GOOGLE_MODELS`: Comma-separated list of models for dropdown (optional)

**Pinecone Settings (Required for External Agent):**
- `PINECONE_API_KEY`: Your Pinecone API key (required for external agent)

**OpenAI Settings (Required for External Agent Embeddings):**
- `OPENAI_API_KEY`: Your OpenAI API key (required for external agent embeddings, even if using different LLM provider)

**Important**: 
- You can configure multiple LLM providers in `.env`. The UI will show all configured providers in the dropdown, allowing you to switch between them per-request. The `LLM_PROVIDER` variable only sets the default.
- **Pinecone and OpenAI are required** for the external agent to work. Even if you use a different LLM provider for queries, you still need OpenAI for generating embeddings.

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

**Frontend Features:**
- **Provider & Model Selection**: Dropdowns at top of chat to select LLM provider and model
- **Document Sidebar**: Left side shows uploaded documents with checkboxes
- **Upload Button**: Click "Upload PDF" to upload new documents
- **Flexible Document Selection**: Three scenarios supported:
  - **Scenario 1**: Select one document, mention another in query → Uses both documents
  - **Scenario 2**: Select multiple documents, query mentions documents → Uses only selected documents (respects manual selection)
  - **Scenario 3**: No selection, query mentions documents → Auto-detects from query
- **Chat Interface**: Right side for asking questions with markdown-formatted responses
- **Progress Timeline**: Real-time visual progress showing agent execution status
- **Structured Quotes**: Click "Internal Agent + Document" below responses to see extracted quotes with section references and accuracy percentages
- **Structured Chunks**: Click "External Agent" below responses to see WIPO document chunks with file name, chunk ID, similarity score, and full text
- **Quote Accuracy Validation**: Each quote shows accuracy percentage (0-100%) based on exact match with document text
- **Streaming Responses**: Watch responses stream in real-time as they're generated

### Option 2: Using Helper Scripts (Recommended)

#### Step 1: Start MCP Server with Logs

```bash
./start_server.sh
```

This script:
- Starts the server in the background
- Shows logs in real-time
- Logs are written to `/tmp/mcp_server.log`
- Press Ctrl+C to stop viewing logs (server keeps running in background)

**Note**: The server will continue running in the background. You can verify it's running by checking:
```bash
curl http://localhost:8000/health
```

#### Step 2: Start Frontend

In a **new terminal window**:

```bash
cd frontend
npm run dev
```

This will:
- Start the frontend on `http://localhost:3000`
- The frontend connects to the MCP server at `http://localhost:8000`
- You'll see frontend logs in this terminal

**To view MCP server logs separately**, use:
```bash
tail -f /tmp/mcp_server.log
```

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
│   │   └── mcp_server.py          # FastAPI server with upload/document endpoints
│   ├── agents/
│   │   ├── internal_agent.py      # Internal document agent (uses uploaded PDFs)
│   │   └── external_agent.py      # External agent (Pinecone vector search for WIPO)
│   ├── uploads/
│   │   └── wipo_documents/        # WIPO PDF documents (processed and uploaded to Pinecone)
│   ├── data_extraction.py         # Script to process WIPO PDFs and upload to Pinecone
│   ├── orchestrator/
│   │   └── orchestrator.py        # Query orchestration with document matching
│   ├── services/
│   │   ├── ollama_service.py      # Ollama API wrapper
│   │   └── document_storage.py    # PDF storage and text extraction service
│   ├── uploads/                   # Uploaded PDF files (created on first upload)
│   │   └── .gitkeep               # Keeps directory in git
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
│   │   │       └── route.ts       # Chat API endpoint (forwards to MCP server)
│   │   ├── components/
│   │   │   ├── chat.tsx           # Chat UI component
│   │   │   └── document-sidebar.tsx  # Document upload and selection sidebar
│   │   └── page.tsx               # Main page with sidebar layout
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

### Issue: LLM provider connection errors

**For Ollama:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
# macOS: Open Ollama.app
# Linux: ollama serve
```

**For OpenAI/Anthropic/Google:**
- Verify API key is correct in `.env`
- Check API key has proper permissions
- Verify you have credits/quota available
- Check network connectivity

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
- **Ollama**: Normal with local CPU inference - responses take 10-60 seconds. Consider GPU acceleration or faster models
- **OpenAI/Anthropic/Google**: Usually faster (3-15 seconds). If slow, check network or API status
- You can switch providers in the UI to compare performance

### Issue: PDF upload fails

**Solution:**
1. Ensure file is a valid PDF (text-based, not scanned images)
2. Check `backend/uploads/` directory exists and is writable
3. Verify pdfplumber is installed: `pip install pdfplumber`
4. Check server logs for extraction errors

### Issue: External agent not working

**Solution:**
1. Verify Pinecone API key is set in `.env`: `PINECONE_API_KEY=your-key`
2. Verify OpenAI API key is set in `.env`: `OPENAI_API_KEY=sk-your-key` (required for embeddings)
3. Check that WIPO documents have been processed:
   ```bash
   python3 -m backend.data_extraction
   ```
4. Verify Pinecone index exists and has data (check Pinecone dashboard)
5. Check server logs for external agent errors

### Issue: Documents not being auto-detected

**Solution:**
1. Check logs for `📚 Available documents:` - should show your uploaded files
2. Try mentioning the exact filename in query (e.g., "italy-111" for "Italy-111.pdf")
3. Fallback matching should catch simple cases (e.g., "italy" → "Italy-111.pdf")
4. Check logs for `📄 Auto-detected documents:` or `🔍 Fallback matching:`
5. You can always manually select documents via checkboxes

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

### Document Upload Flow

1. **User uploads PDF**: Via "Upload PDF" button in sidebar
2. **Backend receives file**: `/api/upload` endpoint
3. **Text extraction**: pdfplumber extracts text from all pages
4. **Storage**: 
   - PDF saved to `backend/uploads/` directory
   - Extracted text cached in memory for fast access
5. **Document appears**: In sidebar with checkbox for selection

### Query Processing Flow

When a user submits a query:

1. **Query Reception**: Frontend sends query (and optionally selected documents) to `/orchestrate` endpoint
2. **Document Detection**: Orchestrator:
   - Gets list of all available documents
   - If query mentions documents (e.g., "italy document"), automatically matches them
   - Combines manually selected + auto-detected documents
3. **Query Analysis**: Orchestrator uses selected LLM provider/model to:
   - Determine which agents are needed
   - Generate optimized queries for each agent (with document context)
4. **Agent Execution**: 
   - **Internal Agent**: If documents selected, retrieves document text and includes it in LLM prompt
   - **External Agent**: Queries external databases
   - Agents execute in sequence
   - Each agent uses the selected LLM provider/model to generate responses
5. **Result Synthesis**: Orchestrator:
   - Uses the same LLM provider/model as previous steps
   - Compares results from all agents
   - Synthesizes a comprehensive answer
6. **Response**: Final answer returned to frontend

### Example Query Flow

**User Query**: "can you tell me from my italy-111 document what i need to change for it to work in australia"

**Step 0 - Document Detection**:
- Orchestrator sees available documents: `['Italy-111.pdf', 'japan-111.pdf']`
- LLM matches "italy-111" → `['Italy-111.pdf']`
- Document auto-detected and selected

**Step 1 - Analysis**:
- Determines: Both `internal_agent` and `external_agent` needed
- Generates queries:
  - Internal: "Look at Italy-111 document and provide all important quoted annexes, codes, terms, and requirements that need to be compared for Australia"
  - External: "Find Australian compliance standards and regional requirements"

**Step 2 - Execution**:
- Internal agent receives `Italy-111.pdf` document text (1409 chars)
- Internal agent includes document text in prompt (total: 1652 chars)
- Internal agent returns contract information based on actual document
- External agent returns compliance requirements

**Step 3 - Synthesis**:
- Orchestrator compares both results
- Generates comprehensive answer
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
| `LLM_PROVIDER` | `ollama` | Default LLM provider (ollama, openai, anthropic, google) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3:latest` | Default Ollama model |
| `OLLAMA_MODELS` | (same as OLLAMA_MODEL) | Comma-separated models for dropdown |
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4` | Default OpenAI model |
| `OPENAI_MODELS` | (same as OPENAI_MODEL) | Comma-separated models for dropdown |
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Default Anthropic model |
| `ANTHROPIC_MODELS` | (same as ANTHROPIC_MODEL) | Comma-separated models for dropdown |
| `GOOGLE_API_KEY` | (required) | Google API key |
| `GOOGLE_MODEL` | `gemini-pro` | Default Google model |
| `GOOGLE_MODELS` | (same as GOOGLE_MODEL) | Comma-separated models for dropdown |
| `PINECONE_API_KEY` | (required) | Pinecone API key for external agent |
| `OPENAI_API_KEY` | (required) | OpenAI API key for external agent embeddings |

---

## API Endpoints

### MCP Server (Port 8000)

- `GET /health` - Health check
- `GET /api/providers` - Get list of configured LLM providers
- `GET /api/models?provider=ollama` - Get available models for a provider
- `POST /orchestrate` - Process user query
  ```json
  {
    "query": "your query here",
    "selected_documents": ["document1.pdf"],  // Optional: manually selected documents
    "provider": "openai",  // Optional: override default provider
    "model": "gpt-4"  // Optional: override default model
  }
  ```
- `POST /api/upload` - Upload a PDF document
  - Content-Type: `multipart/form-data`
  - Body: `file` (PDF file)
  - Returns: Document info (filename, upload date, text length)
- `GET /api/documents` - List all uploaded documents
  - Returns: Array of document objects with filename, upload date, text length
- `DELETE /api/documents/{filename}` - Delete a document
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

## Using Cursor AI to Set Up

This guide is designed to work with Cursor AI. After cloning the repository:

1. **Open the project in Cursor**
2. **Ask Cursor**: "Read SETUP.md and help me set up this project step by step"
3. **Cursor will guide you** through each step, checking prerequisites and helping with configuration
4. **Ask Cursor**: "Read WORKFLOW.md and explain how the system works"
5. **Cursor can help** with troubleshooting if you encounter issues

All documentation includes clear examples and step-by-step instructions that Cursor can follow and explain.

---

**Last Updated**: November 2024

