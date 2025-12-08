# Quick Start Guide

Get up and running in 5 minutes!

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
# Edit .env - at minimum set LLM_PROVIDER and your API key if using cloud provider
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
OPENAI_MODEL=gpt-4
```

## Running

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python3 -m uvicorn backend.server.mcp_server:app --host 0.0.0.0 --port 8000
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

- "What does my italy document say?"
- "Compare my italy and japan documents"
- "What do I need to change in my italy contract for australia?"

## Troubleshooting

- **Backend not starting**: Check Python version, activate venv, install dependencies
- **Frontend not starting**: Check Node version, run `npm install`
- **Ollama errors**: Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- **OpenAI errors**: Check API key in `.env`
- **No providers showing**: Ensure at least one provider is configured in `.env`

## Using Cursor AI

After cloning, open in Cursor and ask:
- "Read QUICKSTART.md and help me set up this project"
- "What do I need to configure in the .env file?"
- "How do I start the servers?"

For detailed help, see [SETUP.md](./SETUP.md) or [README.md](./README.md).
