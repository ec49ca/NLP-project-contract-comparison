# MCP Server Client

A simple web interface for querying MCP (Model Context Protocol) servers.

## Features

- **Simple Chat Interface**: Clean, minimal UI for interacting with MCP servers
- **Agent Discovery**: Automatically discovers available agents from MCP server
- **Query Forwarding**: Forwards queries to MCP server orchestrator endpoint

## Setup

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up environment variables**
   ```bash
   cp .env.local.example .env.local
   # Add your MCP server URL
   MCP_SERVER_URL=http://localhost:8000
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Start your MCP server** (in separate terminal)
   ```bash
   # Your MCP server should be running on port 8000
   ```

## Configuration

### Environment Variables

- `MCP_SERVER_URL`: URL of the MCP server (defaults to `http://localhost:8000`)

## Usage

1. Start both the frontend and MCP server
2. Open the frontend in your browser
3. Type queries in the chat interface
4. Queries are forwarded to the MCP server's `/orchestrate` endpoint

## Architecture

```
Frontend (Next.js) → /api/chat → MCP Server /orchestrate → Agents → Response
```
