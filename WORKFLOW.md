# System Workflow - Based on Log Analysis

This document describes the actual workflow of the MCP server system based on observed logs. It shows how documents are uploaded, how queries are processed, and how the system uses uploaded PDF documents to answer questions.

**Current System Features:**
- **LangGraph Orchestrator**: Uses LangGraph for parallel agent execution
- **Streaming Responses**: Server-Sent Events (SSE) for real-time progress and streaming text
- **Progress Timeline**: Visual UI showing agent execution status
- **Structured Quote Extraction**: Internal agent extracts quoted clauses with section references
- **Query-Aware Extraction**: Internal agent extracts only information relevant to the specific query
- **Markdown Formatting**: Professional paralegal-style reports with structured formatting

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

## Document Upload Workflow

### Document Upload Process

**Log Evidence:**
```
📄 Document uploaded: Italy-111.pdf
Saved document: Italy-111.pdf (1376 characters)
```

**What Happens:**
1. User clicks "Upload PDF" in frontend sidebar
2. Frontend sends POST request to `/api/upload` with PDF file
3. Backend validates file is PDF
4. PDF saved to `backend/uploads/` directory
5. pdfplumber extracts text from all pages
6. Text stored in memory cache: `{filename: {text, uploaded_at, filepath}}`
7. Document appears in sidebar with checkbox

**Storage:**
- **Filesystem**: PDF files stored in `backend/uploads/` (persists across restarts)
- **Memory**: Extracted text cached for fast access during queries
- **On startup**: System loads existing PDFs and extracts text automatically

---

## Query Processing Workflow

### Step 0: Request Reception

**Log Evidence:**
```
🌐 SERVER: Received orchestrate request
   Query: [user's query text]
   Selected documents: ['Italy-111.pdf']  // If manually selected
   Provider override: openai  // If user selected different provider
   Model override: gpt-4  // If user selected different model
```

- Frontend sends POST request to `/orchestrate` endpoint
- May include `selected_documents` array if user selected documents via checkboxes
- May include `provider` and `model` if user selected different LLM provider/model in UI
- Server receives the query and logs it
- If provider override is specified, creates a new LLM service instance for this request
- Query is passed to the Orchestrator with LLM service override

---

### Step 1: Document Detection & Query Analysis

**Log Evidence:**
```
🎯 ORCHESTRATOR: Starting to process query
📚 Available documents: ['Italy-111.pdf', 'japan-111.pdf']
🔍 STEP 1: Analyzing query and determining which agents to use...
📡 OLLAMA: Calling llama3:latest API...
   Prompt length: [X] chars
   System prompt: [Y] chars (includes document list)
✅ OLLAMA: Received response ([Z] chars)
✅ OLLAMA: Successfully parsed JSON response
📄 Auto-detected documents: ['Italy-111.pdf']  // If LLM matched
🔍 Fallback matching: 'Italy-111.pdf' matched from query  // If fallback used
✅ Query analysis complete!
   Agents needed: ['internal_agent', 'external_agent']
   Generated queries: {
     'internal_agent': '[optimized query with document context]',
     'external_agent': '[optimized query]'
   }
   Final selected documents: ['Italy-111.pdf']
```

**What Happens:**
1. Orchestrator gets list of all available documents from document storage
2. **Document Selection Logic** - Handles three scenarios:
   - **Scenario 1**: If documents are manually selected AND query mentions other documents → Uses selected + detects additional from query
     - Example: Select `Australia-111.pdf`, query "compare australia and japan documents" → Processes both Australia and Japan
   - **Scenario 2**: If documents are manually selected AND query just mentions "documents" → Uses ONLY selected documents (respects manual selection)
     - Example: Select `Australia-111.pdf` and `Japan-111.pdf`, query "compare these two documents" → Processes only the 2 selected (won't add Italy even if available)
   - **Scenario 3**: If no documents are manually selected → Uses full fallback matching to detect from query
     - Example: No selection, query "compare these two documents" → Auto-detects and processes documents from query
3. Orchestrator receives the user query (and optionally manually selected documents)
3. Orchestrator uses the LLM service (either default from env or override from request)
4. Orchestrator sends to LLM:
   - User query
   - List of all available documents
   - Instructions to match documents from query
5. LLM analyzes and returns:
   - Which agents are needed
   - **Matched documents** (if query mentions documents)
   - Optimized queries for each agent
6. **Fallback matching** (if LLM doesn't match):
   - Simple string matching: checks if query contains document name keywords
   - Example: "italy" in query → matches "Italy-111.pdf"
6. Documents are combined: manual selection + auto-detected
7. Response is parsed as JSON
   - If JSON parsing fails, fallback parsing extracts all fields including `matched_documents`

**Example from Logs:**
- Query: "can you tell me from my italy-111 document what i need to change for it to work in australia"
- Available documents: `['Italy-111.pdf', 'japan-111.pdf']`
- Document detection: "italy-111" → `['Italy-111.pdf']` (auto-detected)
- Analysis Result:
  - Agents needed: `['internal_agent', 'external_agent']`
  - Matched documents: `['Italy-111.pdf']`
  - Internal agent query: "Look at Italy-111 document and provide all important quoted annexes, codes, terms, and requirements that need to be compared for Australia"
  - External agent query: "Find Australian compliance standards and regional requirements"

---

### Step 2: Agent Execution (LangGraph - Parallel Processing)

**Current System**: Uses LangGraph orchestrator for parallel agent execution.

**Log Evidence:**
```
🎯 LANGGRAPH ORCHESTRATOR: Starting query processing
📊 Analyzing query...
📋 Planning agent calls...
   → Agent Call 1: internal_agent with document Italy-111.pdf
      Query: [optimized query specific to Italy-111.pdf]
   → Agent Call 2: internal_agent with document japan-111.pdf
      Query: [optimized query specific to japan-111.pdf]
🚀 Executing agents in parallel...
   → Executing internal_agent for Italy-111.pdf...
      📋 Full query for internal_agent: [optimized query]
      📄 Documents being sent to internal_agent: ['Italy-111.pdf']
      🔵 INTERNAL AGENT: Processing query...
      📄 Using selected documents: ['Italy-111.pdf']
      📄 Document context retrieved: 1409 characters
      📝 Enhanced prompt length: 1652 characters
      📝 Enhanced prompt (first 500 chars): 
         Query/Instruction: [specific query]
         Available Documents:
         === Document: Italy-111.pdf ===
         [actual document text...]
      📡 LLM: Calling [model] API ([provider])...
      ✅ LLM: Received response ([X] chars)
      ✅ INTERNAL AGENT: Got response ([X] chars)
      📝 Parsed structured quotes: [N] quotes extracted
   ✅ internal_agent completed successfully

   → Executing internal_agent for japan-111.pdf...
      [Similar process for second document]
   ✅ internal_agent completed successfully
```

**Key Differences with LangGraph:**
- **Parallel Execution**: Multiple agents can run simultaneously (one document per agent)
- **Query-Aware Extraction**: Each agent receives a query optimized for its specific document
- **Structured Quote Extraction**: Internal agent parses its response to extract quoted clauses with section references
- **Progress Updates**: Real-time status updates sent via SSE to frontend
   ✅ external_agent completed successfully
```

**What Happens:**
1. Orchestrator executes agents **in parallel** using LangGraph (one document per agent for better token distribution)
2. For **Internal Agent** (if documents selected):
   - Receives optimized query + list of selected documents
   - Retrieves document text from document storage
   - Builds enhanced prompt: query + full document text
   - Makes LLM call with document context
   - LLM searches through actual document text to answer
3. For **External Agent**:
   - Receives optimized query
   - Embeds query using OpenAI (`text-embedding-3-small`)
   - Performs semantic search on Pinecone vector database (WIPO documents)
   - Retrieves top 5 relevant chunks with citations
   - Builds prompt: query + retrieved WIPO document chunks
   - Makes LLM call to synthesize final answer from retrieved context
4. All agent results are collected

**Execution Order:**
- Agents execute in the order they were determined in Step 1
- Each agent is independent and makes its own LLM API call (using selected provider/model)
- **Internal agent** includes document text in prompt (observed: 1652 chars prompt with 1409 chars document text)
- **External agent** uses query only (observed: ~100 chars prompt)
- Agents can return different response sizes (observed: 1103-1591 chars for internal, 987-1442 chars for external)
- All agents use the same LLM provider/model selected for the request

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
1. Orchestrator collects all agent responses
2. **Extracts structured quotes** from internal agent responses (quoted clauses with section references)
3. **Validates quote accuracy** by matching LLM-extracted quotes against raw document text:
   - Calculates accuracy percentage (0-100%) for each quote
   - Uses fuzzy matching to find exact sentences in document text
   - Logs average accuracy for monitoring
   - Accuracy displayed in UI next to each quote (e.g., `"quote text" -100%`)
4. Combines agent responses, structured quotes, and original user query into a single prompt
4. Makes final LLM call using the same provider/model as used in previous steps:
   - The original user query
   - Results from all executed agents
   - Structured quotes extracted from internal agents
   - Instructions to compare and synthesize with markdown formatting
5. LLM generates a comprehensive final answer with markdown formatting (headers, bold, bullet points, blockquotes)
6. Response is typically longer than individual agent responses (observed: 2970 chars vs 1093/1391)
7. Final response includes:
   - **Interpreted Response**: Markdown-formatted paralegal analysis
   - **Structured Quotes**: Array of extracted quotes grouped by agent, document, topic, and section

**Timing Observations:**
- Synthesis takes ~38 seconds (16:31:23 → 16:32:02)
- This is the longest step, likely because it processes the most data
- With streaming, synthesis progress is visible in real-time via timeline UI

---

### Step 4: Response Return (Streaming)

**Current System**: Uses `/orchestrate/stream` endpoint with Server-Sent Events (SSE).

**Log Evidence:**
```
✅ ORCHESTRATOR: Query processing complete!
🌐 SERVER: Streaming response to client via SSE
   → Sending status: analyzing (20%)
   → Sending status: planning (40%)
   → Sending agent_status: internal_agent (Italy-111.pdf) - running
   → Sending agent_status: internal_agent (Italy-111.pdf) - completed
   → Sending status: executing (80%)
   → Sending status: synthesizing (100%)
   → Streaming content chunks...
   → Sending complete event with structured_quotes
INFO: 127.0.0.1:[port] - "POST /orchestrate/stream HTTP/1.1" 200 OK
```

**What Happens:**
1. Orchestrator completes processing
2. Server streams response via Server-Sent Events (SSE):
   - **Status events**: Progress updates (analyzing → planning → executing → synthesizing)
   - **Agent status events**: Individual agent task status (running, completed)
   - **Content events**: Streaming text chunks of final markdown-formatted response
   - **Complete event**: Final result with `interpreted_response` and `structured_quotes` array
3. Frontend displays:
   - **Progress Timeline**: Visual timeline showing current step and agent execution status
   - **Streaming Text**: Markdown-formatted response streams in real-time
   - **Structured Quotes UI**: Clickable "Internal Agent + Document" dropdowns showing extracted quotes with accuracy percentages
   - **Quote Accuracy**: Each quote displays accuracy percentage (0-100%) based on exact match with document text
4. HTTP 200 OK status indicates success

---

## Complete Timeline Example

Based on the logs for query: "tell me more about the italy document i have" with document "Italy-111.pdf" uploaded

| Time | Step | Duration | Details |
|------|------|----------|---------|
| 20:11:36.258 | Request Received | - | Query received, documents available |
| 20:11:36.258 | Step 1: Analysis | ~10s | LLM analyzes query, matches documents |
| 20:11:46.363 | - Document Detection | - | Auto-detected: ['Italy-111.pdf'] |
| 20:11:46.363 | Step 2: Agent Exec | ~20s | Internal agent executes with document |
| 20:11:46.364 | - Document Retrieval | - | Retrieved 1409 chars of document text |
| 20:11:46.365 | - Internal Agent | ~20s | Processes query + document text (1652 chars prompt) |
| 20:12:06.909 | Step 3: Synthesis | ~23s | LLM synthesizes final answer |
| 20:12:29.325 | Step 4: Response | - | Response returned to client |
| **Total** | **~53 seconds** | | End-to-end processing time |

**Key Difference with Documents:**
- Internal agent prompt includes actual document text (1652 chars vs ~100 chars without)
- LLM searches through real document content, not simulated
- More accurate and specific responses based on actual document content

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

### 3. Parallel Execution (LangGraph)
- Agents execute in parallel when processing multiple documents (one document per agent)
- Each agent makes independent LLM API calls (using selected provider/model)
- Results are collected before synthesis
- Better token distribution: one document per agent instead of multiple documents in one agent call

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
[Document Upload]
    ↓
User uploads PDF → Text extraction → Storage (filesystem + memory)
    ↓
[Query Processing]
User Query (optionally with selected documents)
    ↓
[Server Receives Request]
    ↓
[Step 1: Document Detection & Query Analysis]
    → Get available documents list
    → LLM matches documents from query (or use fallback matching)
    → Combine manual + auto-detected documents
    → LLM determines agents needed
    → Generates optimized queries (with document context)
    ↓
[Step 2: Agent Execution]
    → Execute agents sequentially
    → Internal Agent: Retrieves document text, includes in prompt
    → External Agent: Embeds query, searches Pinecone, includes retrieved WIPO chunks in prompt
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

## Document Management Features

### Two Ways to Select Documents

1. **Manual Selection**:
   - User uploads PDF via sidebar
   - User clicks checkbox next to document
   - Selected documents sent with query
   - Log shows: `📄 Manually selected documents: ['Italy-111.pdf']`

2. **Automatic Detection**:
   - User mentions document in query (e.g., "italy document", "japan-111")
   - Orchestrator sees all available documents
   - LLM matches query text to document names
   - Fallback matching if LLM doesn't match
   - Log shows: `📄 Auto-detected documents: ['Italy-111.pdf']`

3. **Both Together**:
   - User can manually select some documents
   - And mention others in query
   - System combines both: `Final selected documents: ['france-456.pdf', 'Italy-111.pdf']`

### Document Text Usage

When documents are selected:
- Internal agent retrieves full document text from storage
- Text is included in LLM prompt: `Enhanced prompt length: 1652 characters`
- LLM searches through actual document content
- Responses are based on real document text, not simulated

Without documents:
- Internal agent uses query only: `Prompt length: 80-103 chars`
- Responses are generic/simulated

---

## Verification Status

✅ **System is Working Correctly**

Evidence from logs:
- ✅ Server starts and discovers agents successfully
- ✅ PDF uploads work: documents saved and text extracted
- ✅ Document storage loads existing documents on startup
- ✅ Queries are received and processed
- ✅ Document detection works: LLM and fallback matching both functional
- ✅ Documents are passed to internal agent correctly
- ✅ Document text is included in prompts (1652 chars vs 80 chars without)
- ✅ LLM calls are made successfully
- ✅ Agents execute and return results based on actual document content
- ✅ Results are synthesized into final answers
- ✅ Responses are returned to clients
- ✅ Error handling works (JSON parsing fallback, including matched_documents)
- ✅ All steps complete successfully

The workflow is functioning as designed, processing queries through document detection, analysis, agent execution with real document text, and synthesis to produce comprehensive responses based on actual uploaded documents.

