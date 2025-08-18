from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict, Any, Optional, Set, Type
from uuid import UUID
import logging
from contextlib import asynccontextmanager
import asyncpg
from ..meta.meta_agent import MetaAgent
from ..interfaces.agent import AgentInterface

from ..services.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# TODO: add image based processing to ocr -> create vectors based on multimodal
# TODO: create streaming for final ai call and general reasoning


meta_agent = MetaAgent()

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global db_pool
    if db_pool is None:
        database_url = os.getenv("POSTGRES_DATABASE_URL")
        if not database_url:
            raise ValueError("POSTGRES_DATABASE_URL environment variable is not set")
        db_pool = await asyncpg.create_pool(database_url)
        logger.info("Database connection pool created")

    return db_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await auto_register_agents()
    # Initialize database connection
    try:
        logger.info("Initializing database connection")
        db_pool = await get_db_pool()
        logger.info("Database connection initialized")

        # Send a ping query to test the connection
        async with db_pool.acquire() as conn:
            ping_result = await conn.fetchval("SELECT 1 as ping")
            logger.info("Database ping successful", extra={"ping_result": ping_result})

    except Exception as e:
        logger.error(
            "Failed to initialize database connection", extra={"error": str(e)}
        )
    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")
    logger.info("Shutting down MCP server")


app = FastAPI(title="Samvid MCP", version="0.1.0", lifespan=lifespan)

# Enable CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = (
    [origin.strip() for origin in allowed_origins_str.split(",")]
    if allowed_origins_str
    else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    registry_state = await meta_agent.agent_registry.get_registry_state()

    # Check database connection
    db_status = "disconnected"
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error("Database health check failed", extra={"error": str(e)})

    return {
        "status": "healthy",
        "server_initialized": True,
        "agents_count": registry_state.get("total_agents", 0),
        "active_agents": registry_state.get("active_agents", 0),
        "database_status": db_status,
        "version": "0.1.0",
    }


@app.get("/mcp/agents")
async def list_agents():
    """List all registered agents in an MCP-compliant format."""
    return await meta_agent.get_agents()


@app.post("/mcp/execute")
async def execute_agent(request: Dict[str, Any]):
    try:
        query = request.get("query")
        if not query:
            return HTTPException(
                status_code=400,
                detail="Query is required",
            )
        original_query = request.get("original_query")
        reasoning = request.get("reasoning")
        data = request.get("data")
        return await meta_agent.handle_no_agent_available_request(
            query, original_query, reasoning, data
        )
    except Exception as e:
        logger.error("Error executing agent", extra={"error": str(e)})
        return HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/execute/{agent_id}")
async def execute_agent_by_id(agent_id: str, request: Dict[str, Any]):
    try:
        logger.info("Executing agent", extra={"agent_id": agent_id, "request": request})

        if not request.get("query"):
            return HTTPException(status_code=400, detail="Query is required")

        return await meta_agent.handle_execute_tool_via_agent_request(
            agent_id, request.get("query"), request.get("data")
        )
    except Exception as e:
        logger.error(
            "Error executing agent", extra={"agent_id": agent_id, "error": str(e)}
        )
        return HTTPException(status_code=500, detail=str(e))


# POST "/execute/{agent_id}/{tool_id}"
# dev endpoint, so doesn't have to be robust
if os.getenv("ENV") == "development":
    # TODO: UUID hash for tools
    @app.post("/execute/{agent_id}/{tool_id}")
    async def execute_agent_capability(
        agent_id: str, tool_id: str, parameters: Dict[str, Any]
    ):
        """
        Execute a specific tool of an agent.
        This endpoint allows direct execution of agent tools by ID.
        """
        import time

        start_time = time.time()

        try:
            # Get the agent instance
            agent_uuid = UUID(agent_id)
            agent = await meta_agent.agent_registry.get_agent(agent_uuid)

            if not agent:
                return {
                    "success": False,
                    "error": f"Agent with ID {agent_id} not found",
                    "metadata": {
                        "executionTime": (time.time() - start_time) * 1000,
                        "toolVersion": "1.0",
                    },
                    "data": {},
                }

            # Execute the tool
            request = {"command": tool_id, **parameters}
            result = await agent.process_request(request)

            execution_time = (time.time() - start_time) * 1000

            return {
                "success": True,
                "metadata": {
                    "executionTime": execution_time,
                },
                "data": result,
            }

        except ValueError as e:
            execution_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": f"Invalid agent ID: {str(e)}",
                "metadata": {"executionTime": execution_time, "toolVersion": "1.0"},
                "data": {},
            }
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(
                "Error executing tool",
                extra={"agent_id": agent_id, "tool_id": tool_id, "error": str(e)},
            )
            return {
                "success": False,
                "error": str(e),
                "metadata": {"executionTime": execution_time, "toolVersion": "1.0"},
                "data": {},
            }


async def auto_register_agents():
    """
    Automatically discover and register all available agents.
    This function is called on server startup and when the /discover endpoint is hit.
    """
    # Keep track of registered agent classes to avoid duplicates
    registered_agents: Set[Type[AgentInterface]] = set()

    # Dictionary to map agent names to their IDs for easier lookup
    agent_name_to_id = {}

    logger.info("Starting automatic agent discovery and registration")

    # Discover all available agents
    logger.info("Calling discovery.discover_agents()...")
    agent_classes = await meta_agent.discovery.discover_agents()
    logger.info(
        "Discovery returned agent classes",
        extra={"count": len(agent_classes), "classes": list(agent_classes.keys())},
    )

    # Register each discovered agent
    for module_name, agent_class in agent_classes.items():
        try:
            # Skip already registered agent classes
            if agent_class in registered_agents:
                logger.info(
                    "Agent already registered, skipping",
                    extra={"module_name": module_name},
                )
                continue

            # Create default config - can be customized per agent type if needed
            default_config = {}

            # Register the agent and use the deterministic agent_id
            logger.info("Registering agent", extra={"module_name": module_name})
            agent_id = await meta_agent.agent_registry.register_agent(
                agent_class, default_config
            )
            registered_agents.add(agent_class)

            # Get the agent instance to access its name
            agent = await meta_agent.agent_registry.get_agent(agent_id)
            if agent:
                # Store the mapping from agent name to ID for easier lookup
                agent_name_to_id[agent.name] = agent_id
                logger.info(
                    "Mapped agent name to ID",
                    extra={"agent_name": agent.name, "agent_id": agent_id},
                )

            logger.info(
                "Auto-registered agent",
                extra={"module_name": module_name, "agent_id": agent_id},
            )
        except Exception as e:
            logger.error(
                "Error auto-registering agent",
                extra={"module_name": module_name, "error": str(e)},
            )
            import traceback

            logger.error("Traceback", extra={"traceback": traceback.format_exc()})

    logger.info("Auto-registration complete", extra={"count": len(registered_agents)})
    logger.info("Agent name to ID mapping", extra={"mapping": agent_name_to_id})


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.server.mcp_server:app", host="0.0.0.0", port=port, reload=False)
