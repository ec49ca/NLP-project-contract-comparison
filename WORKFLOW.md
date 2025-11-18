# System Workflow - Based on Log Analysis

This document describes the actual workflow of the MCP server system based on observed logs. It shows how a user query flows through the system from input to output.

## System Initialization

When the server starts:

1. **Server Process Starts** - Uvicorn server initializes
2. **Agent Discovery** - System automatically discovers available agents
   - Discovers agent exports from the codebase
   - Found 2 agents: `InternalAgent` and `ExternalAgent`
3. **Agent Registration** - Each agent is registered with a unique ID:
   - `InternalAgent` → ID: `6ccf9095-09dc-55bd-b11f-91c64df1a532`
   - `ExternalAgent` → ID: `0939b671-5fb6-58f5-9e80-de95cd809d27`
4. **Server Ready** - Application startup complete, ready to accept requests

---

## Query Processing Workflow

### Step 0: Request Reception

**Log Evidence:**
```
🌐 SERVER: Received orchestrate request
   Query: [user's query text]
```

- Frontend sends POST request to `/orchestrate` endpoint
- Server receives the query and logs it
- Query is passed to the Orchestrator

---

### Step 1: Query Analysis & Agent Selection

**Log Evidence:**
```
🎯 ORCHESTRATOR: Starting to process query
🔍 STEP 1: Analyzing query and determining which agents to use...
📡 OLLAMA: Calling llama3:latest API...
   Prompt length: [X] chars
   System prompt: [Y] chars
✅ OLLAMA: Received response ([Z] chars)
✅ OLLAMA: Successfully parsed JSON response
✅ Query analysis complete!
   Agents needed: ['internal_agent', 'external_agent']
   Generated queries: {
     'internal_agent': '[optimized query 1]',
     'external_agent': '[optimized query 2]'
   }
```

**What Happens:**
1. Orchestrator receives the user query
2. Makes an LLM call to Ollama (using `llama3:latest` model)
3. LLM analyzes the query and determines:
   - Which agents are needed (can be 0, 1, or multiple)
   - Optimized queries for each selected agent
4. Response is parsed as JSON
   - If JSON parsing fails, fallback parsing is attempted
   - Fallback parsing successfully extracts agent names and queries

**Example from Logs:**
- Query: "can you tell me from my italy-xxx contract what i need to change for it to work in australia"
- Analysis Result:
  - Agents needed: `['internal_agent', 'external_agent']`
  - Internal agent query: "Find Italy-xxx contract terms and required changes for adaptation in Australia"
  - External agent query: "Retrieve Australian compliance standards and regional requirements for the adapted contract"

---

### Step 2: Agent Execution

**Log Evidence:**
```
🤖 STEP 2: Executing 2 agent(s)...
   → Executing internal_agent...
      Query: [optimized query for internal agent]
      🔵 INTERNAL AGENT: Processing query...
      📡 OLLAMA: Calling llama3:latest API...
      ✅ OLLAMA: Received response ([X] chars)
      ✅ INTERNAL AGENT: Got response ([X] chars)
   ✅ internal_agent completed successfully

   → Executing external_agent...
      Query: [optimized query for external agent]
      🟢 EXTERNAL AGENT: Processing query...
      📡 OLLAMA: Calling llama3:latest API...
      ✅ OLLAMA: Received response ([Y] chars)
      ✅ EXTERNAL AGENT: Got response ([Y] chars)
   ✅ external_agent completed successfully
```

**What Happens:**
1. Orchestrator executes agents **sequentially** (one after another)
2. For each agent:
   - Agent receives its optimized query
   - Agent makes its own LLM call to Ollama
   - Agent processes the response
   - Agent returns results to orchestrator
3. All agent results are collected

**Execution Order:**
- Agents execute in the order they were determined in Step 1
- Each agent is independent and makes its own Ollama API call
- Agents can return different response sizes (observed: 1093 chars for internal, 1391 chars for external)

**Timing Observations:**
- Internal agent: ~13 seconds (16:30:55 → 16:31:08)
- External agent: ~15 seconds (16:31:08 → 16:31:23)
- Total agent execution: ~28 seconds for 2 agents

---

### Step 3: Result Synthesis

**Log Evidence:**
```
🔄 STEP 3: Comparing and synthesizing results...
📡 OLLAMA: Calling llama3:latest API...
   Prompt length: [X] chars (includes both agent results)
   System prompt: [Y] chars
✅ OLLAMA: Received response ([Z] chars)
✅ Result synthesis complete!
```

**What Happens:**
1. Orchestrator combines all agent results into a single prompt
2. Makes final LLM call to Ollama with:
   - The original user query
   - Results from all executed agents
   - Instructions to compare and synthesize
3. LLM generates a comprehensive final answer
4. Response is typically longer than individual agent responses (observed: 2970 chars vs 1093/1391)

**Timing Observations:**
- Synthesis takes ~38 seconds (16:31:23 → 16:32:02)
- This is the longest step, likely because it processes the most data

---

### Step 4: Response Return

**Log Evidence:**
```
✅ ORCHESTRATOR: Query processing complete!
🌐 SERVER: Returning response to client
INFO: 127.0.0.1:[port] - "POST /orchestrate HTTP/1.1" 200 OK
```

**What Happens:**
1. Orchestrator completes processing
2. Server returns the synthesized response to the frontend
3. HTTP 200 OK status indicates success
4. Frontend displays the response to the user

---

## Complete Timeline Example

Based on the logs for query: "can you tell me from my italy-xxx contract what i need to change for it to work in australia"

| Time | Step | Duration | Details |
|------|------|----------|---------|
| 16:30:46.130 | Request Received | - | Query received by server |
| 16:30:46.130 | Step 1: Analysis | ~9s | LLM determines agents needed |
| 16:30:55.264 | Step 2: Agent Exec | ~28s | Both agents execute sequentially |
| 16:31:08.188 | - Internal Agent | ~13s | Processes internal documents |
| 16:31:23.843 | - External Agent | ~15s | Processes external compliance |
| 16:31:23.843 | Step 3: Synthesis | ~38s | LLM synthesizes final answer |
| 16:32:02.030 | Step 4: Response | - | Response returned to client |
| **Total** | **~76 seconds** | | End-to-end processing time |

---

## Key Observations from Logs

### 1. Error Handling
- JSON parsing failures are handled gracefully
- Fallback parsing mechanism successfully recovers from malformed JSON
- System continues processing even when initial parsing fails

### 2. Agent Selection
- System can determine 0 agents needed (simple queries)
- System can determine multiple agents needed (complex queries)
- Each agent gets an optimized, focused query

### 3. Sequential Execution
- Agents execute one after another (not in parallel)
- Each agent makes independent Ollama API calls
- Results are collected before synthesis

### 4. Response Sizes
- Analysis step: ~61-465 chars
- Agent responses: ~1093-1391 chars each
- Final synthesis: ~2490-2970 chars (largest)

### 5. Performance
- Total processing time: ~76 seconds for complex query
- Most time spent in synthesis step (~38s)
- Agent execution: ~28s combined
- Analysis: ~9s

---

## Workflow Summary

```
User Query
    ↓
[Server Receives Request]
    ↓
[Step 1: Query Analysis]
    → LLM determines agents needed
    → Generates optimized queries
    ↓
[Step 2: Agent Execution]
    → Execute agents sequentially
    → Each agent calls LLM independently
    → Collect all results
    ↓
[Step 3: Result Synthesis]
    → Combine all agent results
    → LLM synthesizes comprehensive answer
    ↓
[Step 4: Response Return]
    → Return to frontend
    → Display to user
```

---

## Verification Status

✅ **System is Working Correctly**

Evidence from logs:
- ✅ Server starts and discovers agents successfully
- ✅ Queries are received and processed
- ✅ LLM calls are made successfully
- ✅ Agents execute and return results
- ✅ Results are synthesized into final answers
- ✅ Responses are returned to clients
- ✅ Error handling works (JSON parsing fallback)
- ✅ All steps complete successfully

The workflow is functioning as designed, processing queries through analysis, agent execution, and synthesis to produce comprehensive responses.

