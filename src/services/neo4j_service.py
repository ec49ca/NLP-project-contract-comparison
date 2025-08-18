"""
Neo4j Service for Knowledge Graph Storage

Handles connection to Neo4j and provides methods to insert triples.
"""

from multiprocessing import process
from neo4j import GraphDatabase
import os
import logging
import asyncio
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# TODO: create script for importing ttl data, don't just run it and comment it out.


class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "samvidneo4j")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Connected to Neo4j", extra={'uri': uri, 'user': user})

        # Test the connection with a ping
        self.ping()

    def close(self):
        self.driver.close()

    def ping(self):
        """Test the Neo4j connection with a simple query."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record["test"] == 1:
                    logger.info("Neo4j connection successful - ping test passed")
                else:
                    logger.error("Neo4j ping test failed - unexpected result")
                    raise Exception("Neo4j ping test failed")
        except Exception as e:
            logger.error("Neo4j connection failed", extra={'error': str(e)})
            raise Exception(f"Failed to connect to Neo4j: {e}")

    async def execute_cypher_query(
        self, query: str, parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query with optional parameters and return the results."""
        try:

            def _run_query():
                with self.driver.session() as session:
                    result = session.run(query, parameters or {})
                    return [record.data() for record in result]

            # Run the blocking operation in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _run_query)
        except Exception as e:
            logger.error("Failed to execute Cypher query", extra={'error': str(e)})
            raise Exception(f"Failed to execute Cypher query: {e}")

    async def test_get_data(self) -> List[Dict[str, Any]]:
        query = "MATCH (n)-[r]->(m) RETURN n, r, m, r.uuid, r.document_id LIMIT 10"
        return await self.execute_cypher_query(query)

    async def insert_entity(
        self, label: str, properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Insert a single entity (node) into the Neo4j database."""
        properties = properties or {}

        # Build the Cypher query for creating a node
        query = f"CREATE (n:{label} $props) RETURN n"
        parameters = {"props": properties}

        result = await self.execute_cypher_query(query, parameters)
        return result[0] if result else {}

    async def insert_relationship(
        self,
        from_label: str,
        from_properties: Dict[str, Any],
        to_label: str,
        to_properties: Dict[str, Any],
        relationship_type: str,
        relationship_properties: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Insert a relationship between two entities."""
        relationship_properties = relationship_properties or {}

        # Build literal property maps for MERGE patterns
        from_props_str = ", ".join([f"{k}: $from_{k}" for k in from_properties.keys()])
        to_props_str = ", ".join([f"{k}: $to_{k}" for k in to_properties.keys()])

        # Build Cypher query to match/create nodes and create relationship
        query = f"""
		MERGE (from:{from_label} {{{from_props_str}}})
		MERGE (to:{to_label} {{{to_props_str}}})
		CREATE (from)-[r:{relationship_type} $rel_props]->(to)
		RETURN from, r, to
		"""

        # Flatten parameters with prefixes to avoid conflicts
        parameters = {}
        for k, v in from_properties.items():
            parameters[f"from_{k}"] = v
        for k, v in to_properties.items():
            parameters[f"to_{k}"] = v
        parameters["rel_props"] = relationship_properties

        result = await self.execute_cypher_query(query, parameters)
        return result[0] if result else {}

    async def clear_database(self) -> Dict[str, Any]:
        """Clear the entire Neo4j database by deleting all nodes and relationships."""

        # return if not in development
        if os.getenv("ENV") != "development":
            return {
                "status": "failure",
                "message": "Cannot clear database if not in dev",
            }

        try:
            # Delete all relationships first, then all nodes
            query = "MATCH (n) DETACH DELETE n"
            await self.execute_cypher_query(query)

            logger.info("Neo4j database cleared successfully")
            return {"status": "success", "message": "Database cleared successfully"}
        except Exception as e:
            logger.error("Failed to clear Neo4j database", extra={'error': str(e)})
            raise Exception(f"Failed to clear Neo4j database: {e}")
