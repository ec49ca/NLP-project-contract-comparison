# Samvid MCP Architecture & Contributor Guide

## 1. High-Level Overview

Samvid MCP is a modular, agent-based system for Model Context Protocol (MCP) operations. It is designed for extensibility, reliability, and clarity, supporting dynamic agent discovery, robust routing, and clean separation of concerns.

---

## 2. Directory Structure

- `src/agents/` — All agent implementations (e.g., `kg_agent.py`, `meta_agent.py`, etc.)
  - `tools/` — Pluggable tools used by agents (e.g., `extract_triples.py`)
- `src/interfaces/` — Agent interface definition (`agent.py`)
- `src/registry/` — Agent registration, state management, and registry models
- `src/routing/` — Routing logic for mapping primitives to agents
- `src/server/` — FastAPI server and API endpoints
- `src/services/` — Integrations (e.g., Neo4j, OpenAI) and configuration
- `src/discovery/` — Agent discovery logic
- `src/constants.py` — Project-wide constants (e.g., UUID namespace)

---

## 3. Core Concepts

### Agents
- Python classes implementing `AgentInterface`.
- Expose capabilities (primitives) and handle requests via `process_request()`.
- Registered and managed by the registry; discovered automatically at startup.

### Tools
- Modular, reusable components for agent logic (see `src/agents/tools/`).

### Registry
- Manages agent lifecycle, registration, and state.
- Only place where agent UUIDs are set on agent instances.

### Routing
- Maps primitives (capabilities) to agent UUIDs.
- `AgentRouter` (`src/routing/router.py`) handles all routing logic.

### API Server
- FastAPI (`src/server/mcp_server.py`) exposes endpoints for agent management, invocation, discovery, and routing.
- All agent and route management is performed via these endpoints.

### Discovery
- Dynamically discovers all agent classes in the codebase at startup.
- `AgentDiscovery` (`src/discovery/agent_discovery.py`) scans the agents directory and registers all valid agent classes.

### Services
- Integrations with external systems (e.g., Neo4j, OpenAI).
- Example: `Neo4jService` handles all graph database operations for the knowledge graph agent.

---

## 4. Logic Flow

### Agent Registration & Discovery
- On startup, the server calls `auto_register_agents()`, which uses `AgentDiscovery` to find all agent classes.
- Each agent is registered via the registry, which instantiates, initializes, and sets the UUID on the agent instance.

### Routing
- Primitives (capabilities) are mapped to agent UUIDs via the router.
- When a request for a primitive is received, the router looks up the agent UUID, retrieves the agent from the registry, and forwards the request to the agent's `process_request()` method.

### Agent Invocation
- The client calls an endpoint (e.g., `/primitives/{primitive_name}`), which is routed to the correct agent and capability.
- The agent processes the request and returns the result.

---

## 5. Best Practices & Contribution Guidelines
- Never generate or assign agent UUIDs outside the registry.
- Always use the agent's `uuid` property for identity.
- Document new agents, tools, and capabilities.
- Add tests for new features and bug fixes.
- Keep code modular, readable, and maintainable.
- Update this document and the README when making architectural changes.

---

## 6. External Integrations
- **Neo4j:** Used for knowledge graph storage (`src/services/neo4j_service.py`).
- **OpenAI:** Used for NLP tasks (`src/services/openai_service.py`).

---

## 7. Configuration
- **Constants:** `src/constants.py` (e.g., UUID namespace)
- **Service Config:** `src/services/config.py` (e.g., API keys, DB URIs)

---

For step-by-step instructions on creating new agents and usage examples, see the README.