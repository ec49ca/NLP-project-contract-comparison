"""
PGVector Service for Vector Storage and Retrieval

Handles connection to PostgreSQL with pgvector extension and provides methods
for executing queries and vector-based retrieval.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
import asyncpg

logger = logging.getLogger(__name__)


class PGVectorService:
    def __init__(self):
        self.database_url = os.getenv(
            "POSTGRES_DATABASE_URL",
            "postgresql://postgres:samvidpg@localhost:5432/samvid_vectors",
        )
        self.pool = None

    async def initialize(self):
        """Initialize the connection pool and test the connection."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=10, command_timeout=60
            )
            logger.info(
                f"Connected to PostgreSQL with pgvector at {self.database_url.split('@')[-1]}"
            )

            # Test the connection
            await self.ping()

        except Exception as e:
            logger.error(f"❌ Failed to initialize PGVectorService: {e}")
            raise Exception(f"Failed to connect to PostgreSQL: {e}")

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PGVector connection pool closed")

    async def ping(self):
        """Test the PostgreSQL connection with a simple query."""
        try:
            result = await self.execute_query("SELECT 1 as test")
            if result and result[0]["test"] == 1:
                logger.info("✅ PostgreSQL connection successful - ping test passed")
            else:
                logger.error("❌ PostgreSQL ping test failed - unexpected result")
                raise Exception("PostgreSQL ping test failed")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise Exception(f"Failed to ping PostgreSQL: {e}")

    async def execute_query(
        self, query: str, parameters: List[Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query with optional parameters and return the results."""
        if not self.pool:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                if parameters:
                    result = await conn.fetch(query, *parameters)
                else:
                    result = await conn.fetch(query)

                # Convert asyncpg.Record objects to dictionaries
                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Failed to execute SQL query: {e}")
            raise Exception(f"Failed to execute SQL query: {e}")

    async def vector_similarity_search(
        self,
        table_name: str,
        vector_column: str,
        query_vector: List[float],
        similarity_threshold: float = 0.7,
        limit: int = 10,
        additional_filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using pgvector cosine similarity.

        Args:
            table_name: Name of the table to search
            vector_column: Name of the vector column
            query_vector: The vector to search for similar items
            similarity_threshold: Minimum similarity score (0-1)
            limit: Maximum number of results to return
            additional_filters: Optional SQL WHERE clause for additional filtering

        Returns:
            List of matching records with similarity scores
        """
        if not self.pool:
            await self.initialize()

        try:
            # Build the similarity query using cosine similarity
            where_clause = ""
            if additional_filters:
                where_clause = f"WHERE {additional_filters} AND"
            else:
                where_clause = "WHERE"

            query = f"""
                SELECT *,
                       1 - ({vector_column} <=> $1) AS similarity_score
                FROM {table_name}
                {where_clause} 1 - ({vector_column} <=> $1) >= $2
                ORDER BY {vector_column} <=> $1
                LIMIT $3
            """

            parameters = [query_vector, similarity_threshold, limit]

            async with self.pool.acquire() as conn:
                result = await conn.fetch(query, *parameters)

                # Convert asyncpg.Record objects to dictionaries
                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Failed to execute vector similarity search: {e}")
            raise Exception(f"Failed to execute vector similarity search: {e}")
