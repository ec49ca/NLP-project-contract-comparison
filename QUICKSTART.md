# Quick Start Guide

Get up and running in 5 minutes!

**Note**: This guide is for local development. The system runs as two separate processes (backend on port 8000, frontend on port 3000) and requires external services (Pinecone, OpenAI for embeddings). For production deployment to AWS, see [SETUP.md](./SETUP.md#aws-deployment-considerations) and [README.md](./README.md#aws-deployment-guide).

## Prerequisites Check

```bash
# Check Python
python3 --version  # Should be 3.11+

# Check Node.js
node --version  # Should be 18+

# Check Ollama (if using local LLM)
curl http://localhost:11434/api/tags  # Should return JSON
```

## Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd agentforge  # or your repo name

# 2. Set up Python backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up frontend
cd frontend
npm install
cd ..

# 4. Configure environment
cp env.example .env
# Edit .env - at minimum set:
#   - LLM_PROVIDER and your API key if using cloud provider
#   - PINECONE_API_KEY (required for external agent)
#   - OPENAI_API_KEY (required for external agent embeddings)
```

## Configuration (Choose One)

### Option A: Ollama (Local, Free)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

Make sure Ollama is running:
```bash
# macOS: Open Ollama.app
# Linux: ollama serve
```

### Option B: OpenAI (Cloud, Paid)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
PINECONE_API_KEY=your-pinecone-api-key-here
```

**Note**: Even if using a different LLM provider, you still need `OPENAI_API_KEY` and `PINECONE_API_KEY` for the external agent.

## Set Up WIPO Documents (Required for External Agent)

Before running, process WIPO documents:

```bash
# 1. Place WIPO PDFs in backend/uploads/wipo_documents/
mkdir -p backend/uploads/wipo_documents
# Copy your WIPO PDF files here

# 2. Process and upload to Pinecone
source venv/bin/activate  # Windows: venv\Scripts\activate
python3 -m backend.data_extraction
```

## Running

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
./start_server.sh
# Or manually:
# python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Using the System

1. Open `http://localhost:3000`
2. **Select Provider/Model**: Use dropdowns at top of chat
3. **Upload PDFs**: Click "Upload PDF" in sidebar
4. **Select Documents**: Check boxes or mention in query
5. **Ask Questions**: Type in chat

## Example Queries

- "What does my italy document say?" (internal agent only)
- "Compare my italy and japan documents" (internal agent only)
- "What do I need to change in my italy contract for australia?" (internal + external agents)
- "What are the IP compliance requirements for my product?" (external agent only)

## Troubleshooting

- **Backend not starting**: Check Python version, activate venv, install dependencies
- **Frontend not starting**: Check Node version, run `npm install`
- **Ollama errors**: Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- **OpenAI errors**: Check API key in `.env`
- **No providers showing**: Ensure at least one provider is configured in `.env`
- **External agent not working**: 
  - Check `PINECONE_API_KEY` and `OPENAI_API_KEY` are set in `.env`
  - Run `python3 -m backend.data_extraction` to process WIPO documents
  - Verify Pinecone index exists and has data

## Using Cursor AI

After cloning, open in Cursor and ask:
- "Read QUICKSTART.md and help me set up this project"
- "What do I need to configure in the .env file?"
- "How do I start the servers?"

For detailed help, see [SETUP.md](./SETUP.md) or [README.md](./README.md).
