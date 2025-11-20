# Contract Comparisons - MCP Server with Multi-Agent Orchestration

**Using WIPO to give recommendations**

A Model Context Protocol (MCP) server with multi-agent orchestration capabilities, featuring a simple web interface for querying agents. This system supports multiple LLM providers (Ollama, OpenAI, Anthropic, Google) and orchestrates multiple agents to process complex queries with document management.

## Features

- **MCP-Compliant**: Implements Model Context Protocol standards
- **FastAPI Server**: Modern async Python web framework
- **Multi-Agent Orchestration**: Intelligent query splitting and result synthesis
- **PDF Document Upload**: Upload and manage PDF documents with automatic text extraction
- **Document Selection**: Manual selection via UI or automatic detection from query text
- **Smart Document Matching**: Orchestrator automatically matches document names from queries
- **Flexible LLM Provider Support**: Switch between Ollama (local), OpenAI, Anthropic, or Google via UI or environment variables
- **Model Selection**: Choose from available models for your selected provider
- **Web Interface**: Modern Next.js frontend with document management sidebar and provider/model selection
- **Automatic Agent Discovery**: Agents are automatically discovered and registered
- **RESTful API**: Standard HTTP endpoints for agent and document management

## Quick Start

**For detailed setup instructions, see [SETUP.md](./SETUP.md)**

### Prerequisites

- Python 3.11+
- Node.js 18+
- **LLM Provider** (choose one or more):
  - **Ollama** (local, free): Install from [ollama.ai](https://ollama.ai/) and pull a model: `ollama pull llama3:latest`
  - **OpenAI** (cloud, paid): Get API key from [platform.openai.com](https://platform.openai.com/)
  - **Anthropic** (cloud, paid): Get API key from [console.anthropic.com](https://console.anthropic.com/)
  - **Google** (cloud, paid): Get API key from [ai.google.dev](https://ai.google.dev/)

### Quick Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd mcp-server-orchestration  # or whatever you name the repository

# 2. Set up Python backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up frontend
cd frontend
npm install
cd ..

# 4. Configure environment
cp env.example .env
# Edit .env with your LLM provider settings (see Configuration section below)

# 5. Start your LLM provider (if using Ollama)
# macOS: Open Ollama.app
# Linux: ollama serve
# For OpenAI/Anthropic/Google: Just add API key to .env

# 6. Start servers
# Terminal 1: MCP Server
source venv/bin/activate
python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access the frontend at `http://localhost:3000`

### Using the System

1. **Select LLM Provider & Model**: 
   - Use the dropdowns at the top of the chat to select your provider (Ollama, OpenAI, etc.)
   - Choose a model from the available models for that provider
   - The system will use your selection for all LLM calls in that query
2. **Upload Documents**: Click "Upload PDF" in the sidebar to upload text-based PDF files
3. **Select Documents**: 
   - **Manual**: Check the box next to documents you want to query
   - **Automatic**: Just mention the document in your query (e.g., "tell me about my italy document")
4. **Ask Questions**: Type your query in the chat
   - The system will use your selected provider/model
   - Automatically uses selected documents
   - Internal agent searches through actual document text
   - External agent queries external databases (WIPO, etc.)

## Architecture

### Components

1. **MCP Server** (Python/FastAPI)
   - Orchestrates multi-agent workflows
   - LLM-agnostic architecture - supports Ollama, OpenAI, Anthropic, Google
   - Provider can be switched per-request via UI or defaults to `LLM_PROVIDER` env var
   - Runs on port 8000

2. **Frontend** (Next.js/React)
   - Simple chat interface
   - Connects to MCP server
   - Runs on port 3000

3. **Agents**
   - **Internal Agent**: Searches through uploaded PDF documents using extracted text
   - **External Agent**: Queries external databases (e.g., WIPO for compliance information)

4. **Orchestrator**
   - Analyzes user queries using LLM
   - Automatically detects and matches documents from query text
   - Splits queries into agent-specific tasks
   - Synthesizes results from multiple agents
   - Has access to all uploaded documents for intelligent routing

### Workflow

```
User Uploads PDF → Text Extraction (pdfplumber) → Storage (filesystem + memory)
                                                              ↓
User Query + Provider/Model Selection → Orchestrator → Query Analysis (LLM)
                              ↓
                    Get Available Documents List
                              ↓
                    Match Documents from Query (LLM + Fallback)
                              ↓
                    Determine Agents Needed
                              ↓
                    Generate Optimized Queries (with document context)
                              ↓
                    Execute Agents (with selected documents + LLM provider)
                              ↓
                    Internal Agent: Uses document text from storage
                    External Agent: Queries external databases
                    (Both use selected LLM provider/model)
                              ↓
                    Compare & Synthesize Results (LLM)
                              ↓
                    Return Final Answer
```

### Document Management

The system supports two ways to select documents for queries:

1. **Manual Selection**: Users can select documents via checkboxes in the sidebar
2. **Automatic Detection**: Orchestrator automatically detects documents mentioned in queries
   - Example: "tell me about my italy document" → automatically finds "Italy-111.pdf"
   - Works with variations: "italian document", "japan-111", etc.
   - Both methods can work together (manual + auto-detected)

## API Endpoints

### MCP Server (Port 8000)

- `GET /health` - Health check
- `GET /api/providers` - Get list of configured LLM providers
- `GET /api/models?provider=ollama` - Get available models for a provider
- `POST /orchestrate` - Process user query
  ```json
  {
    "query": "your query here",
    "selected_documents": ["document1.pdf", "document2.pdf"],  // Optional
    "provider": "openai",  // Optional: override default provider
    "model": "gpt-4"  // Optional: override default model
  }
  ```
- `POST /api/upload` - Upload a PDF document
  - Content-Type: `multipart/form-data`
  - Body: `file` (PDF file)
- `GET /api/documents` - List all uploaded documents
- `DELETE /api/documents/{filename}` - Delete a document
- `GET /mcp/agents` - List all registered agents
- `GET /mcp/resources` - List all MCP resources
- `POST /discover` - Trigger agent discovery

### Frontend (Port 3000)

- `GET /` - Main chat interface
- `POST /api/chat` - Chat endpoint (forwards to MCP server)

## Project Structure

```
mcp-server-orchestration/        # Project root
├── backend/                      # Backend MCP Server (Python/FastAPI)
│   ├── server/
│   │   └── mcp_server.py          # FastAPI server with upload endpoints
│   ├── agents/
│   │   ├── internal_agent.py      # Internal document agent (uses uploaded PDFs)
│   │   └── external_agent.py      # External database agent
│   ├── orchestrator/
│   │   └── orchestrator.py        # Query orchestration with document matching
│   ├── services/
│   │   ├── ollama_service.py      # Ollama API wrapper
│   │   └── document_storage.py    # PDF storage and text extraction
│   ├── uploads/                   # Uploaded PDF files (created on first upload)
│   ├── interfaces/
│   │   └── agent.py               # Agent interface
│   ├── registry/
│   │   └── registry.py            # Agent registry
│   └── discovery/
│       └── agent_discovery.py     # Auto-discovery
├── frontend/                      # Frontend UI (Next.js)
│   ├── app/
│   │   ├── api/chat/route.ts      # Chat API (forwards to MCP server)
│   │   ├── components/
│   │   │   ├── chat.tsx           # Chat UI component
│   │   │   └── document-sidebar.tsx  # Document upload and selection UI
│   │   └── page.tsx               # Main page with sidebar layout
│   └── package.json
├── requirements.txt               # Python dependencies
├── env.example                    # Environment template
├── SETUP.md                       # Detailed setup guide
└── README.md                      # This file
```

## Configuration

Create a `.env` file from `env.example`:

### Basic Configuration

```env
PORT=8000
LOG_LEVEL=INFO
ENV=development
ALLOWED_ORIGINS=*
```

### LLM Provider Configuration

**Option 1: Ollama (Local, Free)**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
# Optional: Add more models for dropdown
OLLAMA_MODELS=llama3:latest,llama3.1:latest,mistral:latest
```

**Option 2: OpenAI (Cloud, Paid)**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
# Optional: Add more models for dropdown
OPENAI_MODELS=gpt-4,gpt-4-turbo,gpt-3.5-turbo
```

**Option 3: Anthropic (Cloud, Paid)**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Option 4: Google (Cloud, Paid)**
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your-api-key-here
GOOGLE_MODEL=gemini-pro
```

**Note**: You can configure multiple providers in `.env`. The UI will show all configured providers in the dropdown, and you can switch between them per-request. The `LLM_PROVIDER` variable sets the default provider.

## Documentation

- **[SETUP.md](./SETUP.md)** - Comprehensive setup guide with step-by-step instructions
- **[WORKFLOW.md](./WORKFLOW.md)** - Detailed workflow explanation including document upload, processing, and LLM provider architecture
- **[QUICKSTART.md](./QUICKSTART.md)** - Quick start guide for getting up and running in 5 minutes
- **[FUTURE_GOALS.md](./FUTURE_GOALS.md)** - Planned improvements and next steps (LangGraph, WIPO integration, agent enhancements)

## Key Features Explained

### Document Upload & Management

- **Upload PDFs**: Use the sidebar "Upload PDF" button to upload text-based PDF files
- **Text Extraction**: pdfplumber automatically extracts text from all pages
- **Storage**: Documents saved to `backend/uploads/` (persists) + text cached in memory (fast access)
- **Document Selection**: 
  - **Manual**: Check boxes in sidebar
  - **Automatic**: Mention document in query (e.g., "italy document" → finds "Italy-111.pdf")

### How Documents Are Used

1. **Upload**: PDF → Text extraction → Storage
2. **Query**: User asks question (with or without mentioning document)
3. **Detection**: Orchestrator matches documents from query or uses manual selection
4. **Processing**: Internal agent retrieves document text and includes it in LLM prompt
5. **Response**: LLM searches through actual document content to answer

### Example Use Cases

- **"What does my italy contract say?"** → Auto-detects Italy-111.pdf, searches through it
- **"Compare my italy and japan documents"** → Finds both, searches through both
- **"What do I need to change in my italy contract for australia?"** → Uses internal agent (Italy document) + external agent (Australian compliance)

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

Or use the helper script:
```bash
./view_logs.sh
```

### Helper Scripts

- `./start_server.sh` - Start MCP server with log viewing
- `./view_logs.sh` - View MCP server logs

## Troubleshooting

See [SETUP.md](./SETUP.md#troubleshooting) for detailed troubleshooting guide.

Common issues:
- **Ollama not running**: Start Ollama and verify with `curl http://localhost:11434/api/tags`
- **OpenAI/Anthropic/Google errors**: Check API key is set correctly in `.env`
- **Provider not showing in UI**: Ensure API key is set in `.env` for that provider
- **Port conflicts**: Kill processes on ports 8000 or 3000
- **Module not found**: Ensure virtual environment is activated and dependencies installed

## License

[Add your license information here]

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request
