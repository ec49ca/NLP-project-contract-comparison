# Contract Comparisons - MCP Server with Multi-Agent Orchestration

**Using WIPO to give recommendations**

A Model Context Protocol (MCP) server with multi-agent orchestration capabilities, featuring a simple web interface for querying agents. This system supports multiple LLM providers (Ollama, OpenAI, Anthropic, Google) and orchestrates multiple agents to process complex queries with document management.

## Features

- **MCP-Compliant**: Implements Model Context Protocol standards
- **FastAPI Server**: Modern async Python web framework
- **LangGraph Orchestration**: Parallel multi-agent processing with dynamic query splitting
- **Real-Time Streaming**: Server-Sent Events (SSE) for live progress updates and streaming responses
- **Progress Timeline UI**: Visual timeline showing agent execution status and progress
- **Dual-Agent System**: 
  - **Internal Agent**: Analyzes uploaded contract documents, extracts quoted clauses with section references
  - **External Agent**: Queries WIPO compliance databases using Pinecone vector search for regulatory information
- **Structured Quote Extraction**: Internal agent extracts quoted clauses with section references, displayed in clickable UI
- **Structured Chunk Display**: External agent chunks displayed with file name, chunk ID, similarity score, and full text
- **Query-Aware Extraction**: Internal agent extracts only relevant information based on the specific query
- **Markdown-Formatted Responses**: Professional paralegal-style reports with headers, bold text, bullet points, and blockquotes
- **PDF Document Upload**: Upload and manage PDF documents with automatic text extraction
- **WIPO Document Processing**: Process WIPO PDFs and upload to Pinecone for semantic search
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
  - **OpenAI** (cloud, paid): Get API key from [platform.openai.com](https://platform.openai.com/) - **Required for external agent (embeddings)**
  - **Anthropic** (cloud, paid): Get API key from [console.anthropic.com](https://console.anthropic.com/)
  - **Google** (cloud, paid): Get API key from [ai.google.dev](https://ai.google.dev/)
- **Pinecone** (for external agent): Get API key from [pinecone.io](https://www.pinecone.io/) - **Required for WIPO document search**

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
# IMPORTANT: Add PINECONE_API_KEY and OPENAI_API_KEY for external agent

# 5. Set up Pinecone and WIPO documents (for external agent)
# Place WIPO PDFs in backend/uploads/wipo_documents/
# Then process them:
python3 -m backend.data_extraction

# 6. Start your LLM provider (if using Ollama)
# macOS: Open Ollama.app
# Linux: ollama serve
# For OpenAI/Anthropic/Google: Just add API key to .env

# 7. Start servers
# Terminal 1: MCP Server (using helper script)
./start_server.sh

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Note**: The `start_server.sh` script starts the MCP server in the background and shows logs. Alternatively, you can run the server manually:
```bash
source venv/bin/activate
python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000
```

Access the frontend at `http://localhost:3000`

### Using the System

1. **Select LLM Provider & Model**: 
   - Use the dropdowns at the top of the chat to select your provider (Ollama, OpenAI, etc.)
   - Choose a model from the available models for that provider
   - The system will use your selection for all LLM calls in that query
2. **Upload Documents**: Click "Upload PDF" in the sidebar to upload text-based PDF files
3. **Select Documents**: The system supports three flexible document selection scenarios:
   - **Scenario 1**: Select one document, mention another in query → Uses both documents
     - Example: Select `Australia-111.pdf`, query "compare australia and japan documents" → Processes both
   - **Scenario 2**: Select multiple documents, query mentions documents → Uses only selected documents
     - Example: Select `Australia-111.pdf` and `Japan-111.pdf`, query "compare these two documents" → Processes only the 2 selected
   - **Scenario 3**: No selection, query mentions documents → Auto-detects from query
     - Example: No selection, query "compare these two documents" → Auto-detects and processes documents
   - **Manual Selection**: Check boxes next to documents you want to query
   - **Automatic Detection**: Mention document names or countries in your query (e.g., "tell me about my italy document")
4. **Ask Questions**: Type your query in the chat
   - The system will use your selected provider/model
   - Automatically uses selected documents
   - **Progress Timeline**: Watch real-time progress as agents analyze, plan, execute, and synthesize
   - **Structured Quotes**: Click "Internal Agent + Document" below responses to see extracted quotes with section references
   - **Structured Chunks**: Click "External Agent" below responses to see WIPO document chunks with similarity scores
   - Internal agent searches through actual document text (query-aware extraction)
   - External agent queries WIPO compliance databases using Pinecone semantic search
   - Final response is streamed and formatted in markdown for easy reading

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
   - **Internal Agent**: Searches through uploaded PDF documents using extracted text, extracts structured quotes
   - **External Agent**: Queries WIPO compliance databases using Pinecone vector search, returns structured chunks with source information

4. **Orchestrator** (LangGraph-based)
   - Uses LangGraph for parallel agent execution
   - Analyzes user queries using LLM
   - Automatically detects and matches documents from query text
   - Intelligently splits queries into agent-specific tasks (can split multi-part queries across documents)
   - Executes multiple agents in parallel (one document per agent for better token distribution)
   - Synthesizes results from multiple agents with markdown formatting
   - Streams progress updates and final response via SSE
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
- `POST /orchestrate` - Process user query (legacy endpoint, returns complete response)
- `POST /orchestrate/stream` - Process user query with streaming (SSE)
  ```json
  {
    "query": "your query here",
    "selected_documents": ["document1.pdf", "document2.pdf"],  // Optional
    "provider": "openai",  // Optional: override default provider
    "model": "gpt-4"  // Optional: override default model
  }
  ```
  Returns Server-Sent Events (SSE) with:
  - `status` events: Progress updates (analyzing, planning, executing, synthesizing)
  - `agent_status` events: Individual agent task status (running, completed)
  - `content` events: Streaming text chunks of final response
  - `complete` event: Final result with `interpreted_response` and `structured_quotes`
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
│   │   └── external_agent.py      # External agent (Pinecone vector search for WIPO)
│   ├── uploads/
│   │   └── wipo_documents/        # WIPO PDF documents (processed and uploaded to Pinecone)
│   ├── data_extraction.py         # Script to process WIPO PDFs and upload to Pinecone
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

**Pinecone Configuration (Required for External Agent)**
```env
PINECONE_API_KEY=your-pinecone-api-key-here
```

**OpenAI Configuration (Required for External Agent Embeddings)**
```env
OPENAI_API_KEY=sk-your-api-key-here
```

**Note**: 
- You can configure multiple LLM providers in `.env`. The UI will show all configured providers in the dropdown, and you can switch between them per-request. The `LLM_PROVIDER` variable sets the default provider.
- **Pinecone and OpenAI are required** for the external agent to work (Pinecone for vector storage, OpenAI for embeddings). Even if you use a different LLM provider for queries, you still need OpenAI for generating embeddings.

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

- **"What does my italy contract say?"** → Auto-detects Italy-111.pdf, searches through it (internal agent only)
- **"Compare my italy and japan documents"** → Finds both, searches through both (internal agent only)
- **"What do I need to change in my italy contract for australia?"** → Uses internal agent (Italy document) + external agent (WIPO compliance information)
- **"What are the IP compliance requirements for my product?"** → Uses external agent (WIPO database search)

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

## Current State & Architecture Overview

### Project Status

This project is a **fully functional MCP (Model Context Protocol) server** with multi-agent orchestration capabilities. The system is currently in a **production-ready state** for local development and testing, with the following key characteristics:

**Current Implementation:**
- ✅ **Backend**: Python 3.11+ with FastAPI, running on port 8000
- ✅ **Frontend**: Next.js 15+ with React 19, running on port 3000
- ✅ **Orchestration**: LangGraph-based parallel agent execution
- ✅ **Agents**: Two specialized agents (Internal for document analysis, External for WIPO compliance search)
- ✅ **Document Management**: PDF upload, text extraction, and intelligent document matching
- ✅ **LLM Support**: Multi-provider support (Ollama, OpenAI, Anthropic, Google) with per-request switching
- ✅ **Streaming**: Server-Sent Events (SSE) for real-time progress and response streaming
- ✅ **Vector Search**: Pinecone integration for WIPO document semantic search

**Architecture Pattern:**
- **Microservices-style**: Separate backend (FastAPI) and frontend (Next.js) services
- **Agent-based**: Pluggable agent system with automatic discovery
- **Orchestration**: Central orchestrator manages query analysis, agent execution, and result synthesis
- **Stateless Backend**: Document storage is filesystem-based with in-memory caching for performance

**Current Deployment:**
- **Local Development**: Designed for local machine execution
- **Docker Support**: Dockerfile and docker-compose.yml provided for containerization
- **Production Ready**: Code is production-quality but requires infrastructure setup for cloud deployment

### Technology Stack

**Backend Stack:**
- **Framework**: FastAPI (async Python web framework)
- **Server**: Uvicorn (ASGI server)
- **Orchestration**: LangGraph (for parallel agent execution)
- **PDF Processing**: pdfplumber, PyPDF2
- **Vector Database**: Pinecone (for WIPO document search)
- **LLM Integration**: httpx (for Ollama), openai SDK, anthropic SDK, google SDK
- **Token Management**: tiktoken (for text chunking)

**Frontend Stack:**
- **Framework**: Next.js 15 (React framework)
- **UI Library**: React 19
- **Styling**: Tailwind CSS 4
- **Components**: Radix UI primitives
- **Markdown**: react-markdown (for formatted responses)

**External Services:**
- **LLM Providers**: Ollama (local), OpenAI, Anthropic, Google (cloud)
- **Vector Database**: Pinecone (cloud service)
- **Embeddings**: OpenAI (required for external agent, even if using different LLM provider)

## Dependencies Overview

### Python Dependencies (`requirements.txt`)

The backend requires the following Python packages:

**Core Web Framework:**
- `fastapi>=0.100.0` - Modern async web framework for building APIs
- `uvicorn[standard]>=0.20.0` - ASGI server for running FastAPI
- `pydantic>=2.0.0` - Data validation and settings management

**Configuration & Environment:**
- `python-dotenv>=1.0.0` - Loads environment variables from `.env` file

**File Handling:**
- `python-multipart>=0.0.6` - Required for FastAPI file upload endpoints

**PDF Processing:**
- `pdfplumber>=0.10.0` - Extracts text from PDF documents (primary tool)
- `PyPDF2` - Alternative PDF processing for WIPO document extraction

**LLM & AI Services:**
- `httpx>=0.24.0` - Async HTTP client for Ollama API calls
- `openai>=2.8.1` - OpenAI SDK for embeddings and LLM calls
- `tiktoken` - Token counting for text chunking (used in WIPO document processing)

**Vector Database:**
- `pinecone>=8.0.0` - Pinecone client for vector search operations

**Development & Testing:**
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support

**Logging:**
- `structlog>=23.0.0` - Structured logging

**Type Support:**
- `typing-extensions>=4.8.0` - Extended type hints

**Dependency Notes:**
- All dependencies are pinned with minimum versions for compatibility
- No version conflicts known at current state
- Total package count: ~15 direct dependencies (with transitive dependencies, ~50-100 total packages)

### Node.js Dependencies (`frontend/package.json`)

The frontend requires the following Node.js packages:

**Core Framework:**
- `next@^15.3.3` - Next.js framework (React-based)
- `react@^19.1.0` - React library
- `react-dom@^19.1.0` - React DOM rendering

**UI Components:**
- `@radix-ui/react-slot@^1.2.3` - Radix UI primitives
- `lucide-react@^0.511.0` - Icon library

**Styling:**
- `tailwindcss@^4.1.8` - Utility-first CSS framework
- `@tailwindcss/typography@^0.5.16` - Typography plugin
- `@tailwindcss/postcss@^4.1.8` - PostCSS integration
- `autoprefixer@^10.4.21` - CSS vendor prefixing
- `postcss@^8.5.4` - CSS processing

**Utilities:**
- `class-variance-authority@^0.7.1` - Component variant management
- `clsx@^2.1.1` - Conditional class names
- `tailwind-merge@^3.3.0` - Tailwind class merging

**Content Rendering:**
- `react-markdown@^10.1.0` - Markdown rendering for LLM responses

**Development:**
- `typescript@5.8.3` - TypeScript compiler
- `@types/node@22.15.29` - Node.js type definitions
- `@types/react@19.1.6` - React type definitions

**Dependency Notes:**
- All packages are modern versions (Next.js 15, React 19)
- No legacy dependencies
- Total package count: ~15 direct dependencies (with transitive dependencies, ~200-300 total packages in node_modules)

### System Dependencies

**Required System Software:**
- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **npm** or **yarn** - Node package manager
- **Git** - Version control

**Optional but Recommended:**
- **Ollama** - For local LLM inference (if using Ollama provider)
- **Docker** - For containerized deployment
- **Docker Compose** - For multi-container orchestration

**External Service Accounts Required:**
- **Pinecone Account** - Vector database (required for external agent)
- **OpenAI Account** - Embeddings generation (required for external agent, even if using different LLM provider)
- **LLM Provider Account** - At least one of: OpenAI, Anthropic, or Google (if not using Ollama)

## Local Development Setup

### How the System Runs Locally

**Current Local Architecture:**

The system runs as **two separate processes** that communicate over HTTP:

1. **Backend Process** (Port 8000)
   - FastAPI server running via Uvicorn
   - Handles all API requests, document uploads, and orchestration
   - Connects to LLM providers (Ollama local or cloud APIs)
   - Connects to Pinecone for vector search
   - Stores documents in `backend/uploads/` directory

2. **Frontend Process** (Port 3000)
   - Next.js development server
   - Serves the React UI
   - Makes API calls to backend at `http://localhost:8000`
   - Hot-reloads on code changes

**Local Execution Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Development Setup                   │
└─────────────────────────────────────────────────────────────┘

Terminal 1: Backend Server
├─ Activates Python virtual environment (venv)
├─ Starts Uvicorn server: python3 -m uvicorn backend.server.mcp_server:app
├─ Server binds to: 0.0.0.0:8000
├─ Logs written to: /tmp/mcp_server.log
└─ Health check: http://localhost:8000/health

Terminal 2: Frontend Server
├─ Navigates to: cd frontend
├─ Starts Next.js dev server: npm run dev
├─ Server binds to: localhost:3000
├─ Hot reload enabled for development
└─ Connects to backend: http://localhost:8000

External Services (if configured):
├─ Ollama (if LLM_PROVIDER=ollama)
│  └─ Running locally on: http://localhost:11434
├─ OpenAI API (for embeddings, or if LLM_PROVIDER=openai)
│  └─ Cloud service: https://api.openai.com/v1
├─ Anthropic API (if LLM_PROVIDER=anthropic)
│  └─ Cloud service: https://api.anthropic.com
├─ Google API (if LLM_PROVIDER=google)
│  └─ Cloud service: https://generativelanguage.googleapis.com
└─ Pinecone (for external agent)
   └─ Cloud service: https://api.pinecone.io
```

**Local File System Structure:**

```
Project Root/
├── backend/
│   ├── uploads/              # User-uploaded PDFs (created on first upload)
│   │   └── wipo_documents/   # WIPO PDFs for processing
│   └── [source code]
├── frontend/
│   ├── .next/                # Next.js build cache (auto-generated)
│   └── [source code]
├── venv/                     # Python virtual environment
├── .env                      # Environment variables (not in git)
└── [config files]
```

**Local Data Persistence:**

- **Documents**: Stored in `backend/uploads/` (persists across restarts)
- **Document Text Cache**: In-memory only (reloaded on server restart)
- **WIPO Vector Data**: Stored in Pinecone cloud (persists independently)
- **Environment Config**: `.env` file (not committed to git)

**Local Development Workflow:**

1. **Initial Setup** (one-time):
   ```bash
   # Backend setup
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Frontend setup
   cd frontend
   npm install
   cd ..
   
   # Configuration
   cp env.example .env
   # Edit .env with your API keys
   ```

2. **Daily Development**:
   ```bash
   # Terminal 1: Start backend
   source venv/bin/activate
   ./start_server.sh  # or: python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000
   
   # Terminal 2: Start frontend
   cd frontend
   npm run dev
   ```

3. **Access Application**:
   - Open browser: `http://localhost:3000`
   - Backend API: `http://localhost:8000`
   - Health check: `http://localhost:8000/health`

**Local Development Features:**

- ✅ **Hot Reload**: Frontend auto-reloads on code changes
- ✅ **Logging**: Backend logs to `/tmp/mcp_server.log` and console
- ✅ **Error Handling**: Graceful error handling with detailed logs
- ✅ **Development Mode**: Verbose logging and debugging enabled
- ✅ **CORS**: Configured for local development (ALLOWED_ORIGINS=*)

## AWS Deployment Guide

### Overview: Deploying to AWS

While the system is currently designed for local development, it can be deployed to AWS with proper infrastructure setup. This section outlines the recommended AWS deployment architecture and considerations.

### Recommended AWS Architecture

**Option 1: Containerized Deployment (Recommended)**

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Container Architecture                  │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  AWS Application Load Balancer (ALB)                     │
│  - SSL/TLS termination                                   │
│  - Health checks                                         │
│  - Routing rules                                         │
└─────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────┬──────────────────────────┐
    ▼                          ▼                          ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ ECS Service  │      │ ECS Service  │      │ ECS Service  │
│ (Backend)    │      │ (Frontend)   │      │ (Optional)   │
│              │      │              │      │ (Workers)    │
│ Port: 8000   │      │ Port: 3000   │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
    │                      │
    ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│  ECS Cluster (Fargate or EC2)                          │
│  - Auto-scaling groups                                  │
│  - Task definitions                                     │
│  - Service discovery                                    │
└─────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────────────────────────────────┐
    │                                                      │
    ▼                      ▼                              ▼
┌──────────────┐  ┌──────────────┐            ┌──────────────┐
│ EFS          │  │ RDS/ElastiCache│          │ S3 Bucket   │
│ (Document    │  │ (Optional)   │            │ (Static     │
│  Storage)    │  │              │            │  Assets)    │
└──────────────┘  └──────────────┘            └──────────────┘

External Services:
├─ Pinecone (Cloud) - Vector database
├─ OpenAI API (Cloud) - Embeddings
└─ LLM Provider APIs (Cloud) - LLM inference
```

**Option 2: EC2 Deployment (Simpler, Less Scalable)**

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS EC2 Architecture                      │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  EC2 Instance (t3.medium or larger)                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Docker Compose                                  │   │
│  │  ├─ Backend Container (Port 8000)               │   │
│  │  └─ Frontend Container (Port 3000)              │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  EBS Volume (Document Storage)                   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Security Group                                         │
│  - Allow HTTP/HTTPS from internet                       │
│  - Allow SSH from your IP                               │
└─────────────────────────────────────────────────────────┘
```

### AWS Services Required

**Core Infrastructure:**
- **ECS (Elastic Container Service)** or **EC2** - Compute for running containers
- **Application Load Balancer (ALB)** - Load balancing and SSL termination
- **VPC** - Virtual private cloud for network isolation
- **Security Groups** - Firewall rules
- **IAM Roles** - Service permissions

**Storage:**
- **EFS (Elastic File System)** - Shared file storage for documents (if using ECS)
- **EBS Volume** - Block storage for documents (if using EC2)
- **S3 Bucket** - Optional: For static assets, backups, or document storage

**Optional Services:**
- **RDS** - If you want to move document metadata to a database
- **ElastiCache** - For caching document text (instead of in-memory)
- **CloudWatch** - Logging and monitoring
- **Route 53** - DNS management
- **ACM (Certificate Manager)** - SSL/TLS certificates

**External Services (Still Required):**
- **Pinecone** - Vector database (cloud service, not AWS)
- **OpenAI/Anthropic/Google** - LLM providers (cloud services, not AWS)

### Deployment Steps for AWS

**Step 1: Container Preparation**

The project already includes:
- ✅ `Dockerfile` - For backend container
- ✅ `docker-compose.yml` - For local container orchestration

**Additional files needed:**
- Create `Dockerfile.frontend` for frontend container
- Create `docker-compose.prod.yml` for production container setup
- Update environment variables for production

**Step 2: ECS Deployment (Recommended)**

1. **Build and Push Docker Images:**
   ```bash
   # Build backend image
   docker build -t your-ecr-repo/backend:latest .
   
   # Build frontend image (need to create Dockerfile.frontend)
   docker build -f Dockerfile.frontend -t your-ecr-repo/frontend:latest ./frontend
   
   # Push to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
   docker push your-ecr-repo/backend:latest
   docker push your-ecr-repo/frontend:latest
   ```

2. **Create ECS Task Definitions:**
   - Backend task: CPU 1 vCPU, Memory 2GB (minimum)
   - Frontend task: CPU 0.5 vCPU, Memory 1GB
   - Configure environment variables from AWS Secrets Manager or Parameter Store
   - Mount EFS volume for document storage

3. **Create ECS Services:**
   - Configure auto-scaling (min: 1, max: 5 tasks)
   - Set up health checks
   - Configure service discovery

4. **Set Up Load Balancer:**
   - Create ALB with SSL certificate from ACM
   - Configure target groups for backend and frontend
   - Set up routing rules

**Step 3: EC2 Deployment (Simpler Alternative)**

1. **Launch EC2 Instance:**
   - AMI: Amazon Linux 2023 or Ubuntu 22.04
   - Instance type: t3.medium or larger (2 vCPU, 4GB RAM minimum)
   - Storage: 20GB+ EBS volume for documents

2. **Install Dependencies:**
   ```bash
   # Install Docker and Docker Compose
   sudo yum install docker docker-compose -y
   sudo systemctl start docker
   sudo usermod -aG docker ec2-user
   ```

3. **Deploy Application:**
   ```bash
   # Clone repository
   git clone <your-repo-url>
   cd <project-directory>
   
   # Set up environment
   cp env.example .env
   # Edit .env with production values
   
   # Build and run with Docker Compose
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Set Up Reverse Proxy (Nginx):**
   - Install Nginx on EC2
   - Configure SSL with Let's Encrypt
   - Proxy requests to containers

### AWS Configuration Considerations

**Environment Variables in AWS:**

Use AWS Systems Manager Parameter Store or Secrets Manager:
```bash
# Store secrets
aws ssm put-parameter --name "/app/pinecone-api-key" --value "your-key" --type "SecureString"
aws ssm put-parameter --name "/app/openai-api-key" --value "your-key" --type "SecureString"

# In ECS task definition, reference:
{
  "name": "PINECONE_API_KEY",
  "valueFrom": "arn:aws:ssm:region:account:parameter/app/pinecone-api-key"
}
```

**Document Storage Options:**

1. **EFS (Recommended for ECS):**
   - Shared file system across all tasks
   - Persistent storage
   - Auto-scaling
   - Mount in task definition

2. **EBS Volume (For EC2):**
   - Attach to EC2 instance
   - Mount at `/app/backend/uploads`
   - Regular backups recommended

3. **S3 (Alternative):**
   - Store documents in S3
   - Modify code to read from S3 instead of filesystem
   - Use S3 for document storage, cache in memory

**Scaling Considerations:**

- **Backend**: Can scale horizontally (multiple tasks behind load balancer)
- **Frontend**: Can scale horizontally (stateless)
- **Document Storage**: Use EFS for shared access across tasks
- **In-Memory Cache**: Consider ElastiCache (Redis) for document text cache
- **Database**: Consider RDS if moving document metadata to database

**Security Best Practices:**

- ✅ Use IAM roles (not access keys) for AWS service access
- ✅ Store API keys in Secrets Manager or Parameter Store
- ✅ Use VPC for network isolation
- ✅ Configure security groups with least privilege
- ✅ Enable SSL/TLS with ACM certificates
- ✅ Use WAF (Web Application Firewall) for DDoS protection
- ✅ Enable CloudWatch logging and monitoring
- ✅ Regular security updates and patches

**Cost Estimation (Approximate):**

**ECS Fargate (Small Scale):**
- Backend: 1 vCPU, 2GB RAM = ~$30/month
- Frontend: 0.5 vCPU, 1GB RAM = ~$15/month
- ALB: ~$20/month
- EFS: 10GB = ~$3/month
- **Total: ~$68/month** (plus data transfer and external API costs)

**EC2 (t3.medium):**
- Instance: ~$30/month
- EBS Storage: 20GB = ~$2/month
- **Total: ~$32/month** (plus data transfer and external API costs)

**Additional Costs:**
- Pinecone: Free tier available, then pay-per-use
- OpenAI/Anthropic/Google: Pay-per-use API calls
- Data transfer: ~$0.09/GB outbound

### Migration Path from Local to AWS

1. **Phase 1: Containerization**
   - Ensure Dockerfile works locally
   - Test with docker-compose
   - Verify all dependencies work in containers

2. **Phase 2: AWS Setup**
   - Create VPC and networking
   - Set up ECR or use EC2
   - Configure security groups

3. **Phase 3: Deployment**
   - Deploy backend first
   - Test backend endpoints
   - Deploy frontend
   - Test full integration

4. **Phase 4: Production Hardening**
   - Set up monitoring (CloudWatch)
   - Configure auto-scaling
   - Set up backups
   - Enable logging and alerting

### Current Limitations for AWS Deployment

**What Needs to Be Done:**
- ⏳ Frontend Dockerfile needs to be created
- ⏳ Production docker-compose configuration
- ⏳ Environment variable management in AWS
- ⏳ Document storage migration (filesystem → EFS/S3)
- ⏳ Health check endpoints verification
- ⏳ SSL/TLS certificate setup
- ⏳ Domain and DNS configuration

**What Already Works:**
- ✅ Backend Dockerfile exists and is functional
- ✅ Application is containerization-ready
- ✅ Environment-based configuration
- ✅ Health check endpoint exists
- ✅ Stateless backend design (except document storage)

### Future AWS Enhancements

Consider these improvements for production AWS deployment:
- **Serverless Option**: Lambda functions for backend (with API Gateway)
- **CDN**: CloudFront for frontend static assets
- **Database**: RDS for document metadata and user management
- **Caching**: ElastiCache for document text and query results
- **Monitoring**: CloudWatch dashboards and alarms
- **CI/CD**: CodePipeline for automated deployments
- **Multi-Region**: Deploy to multiple regions for high availability

## License

[Add your license information here]

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request
