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

            # TODO: optimize db read/write so doesnt do unnecessary calls. right now calling this every time request is made.
            # create table if it doesn't exist
            await self.create_kg_vector_lookup_table()

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

    async def insert_embedding_lookup(
        self, embedding: List[float], missing_part: str, kg_uuid: str, document_id: str
    ):
        """Insert an embedding into the kg_vector_lookup table."""
        if not self.pool:
            await self.initialize()

        try:
            query = """
				INSERT INTO kg_vector_lookup (embedding, missing_part, kg_uuid, document_id)
				VALUES ($1, $2, $3, $4)
			"""
            await self.execute_query(
                query, [embedding, missing_part, kg_uuid, document_id]
            )
        except Exception as e:
            logger.error(f"Failed to insert embedding lookup: {e}")
            raise Exception(f"Failed to insert embedding lookup: {e}")

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

    async def create_kg_vector_lookup_table(self):
        """Create the kg_vector_lookup table if it doesn't exist."""
        if not self.pool:
            await self.initialize()

        try:
            # TODO: for now using missing_part because not going to do graph traversal; eventually remove this and just look at graph and retrieve more info from there
            query = """
				CREATE TABLE IF NOT EXISTS kg_vector_lookup (
					id SERIAL PRIMARY KEY,
					embedding vector(1536),
					missing_part TEXT NOT NULL,
					kg_uuid TEXT NOT NULL, -- uuid for the triple relationship, not the subject or entity
					document_id TEXT
				);
			"""

            await self.execute_query(query)
            logger.info("✅ kg_vector_lookup table created or already exists")

        except Exception as e:
            logger.error(f"Failed to create kg_vector_lookup table: {e}")
            raise Exception(f"Failed to create kg_vector_lookup table: {e}")

    async def clear_kg_vector_lookup_table(self):
        """Drop the kg_vector_lookup table completely."""
        if not self.pool:
            await self.initialize()

        if os.getenv("ENV") != "development":
            return

        try:
            query = "DROP TABLE IF EXISTS kg_vector_lookup;"
            await self.execute_query(query)
            logger.info("✅ kg_vector_lookup table dropped successfully")

        except Exception as e:
            logger.error(f"Failed to drop kg_vector_lookup table: {e}")
            raise Exception(f"Failed to drop kg_vector_lookup table: {e}")

    async def get_all_embeddings_and_kg_uuids(self) -> List[Dict[str, Any]]:
        """
        Retrieve all embeddings and kg_uuid values from the kg_vector_lookup table.

        Returns:
                List of dictionaries containing 'embedding' and 'kg_uuid' for each record
        """
        if not self.pool:
            await self.initialize()

        try:
            query = """
				SELECT embedding, kg_uuid, missing_part, document_id
				FROM kg_vector_lookup
				ORDER BY id
			"""

            result = await self.execute_query(query)
            logger.info(
                f"Retrieved {len(result)} embeddings and kg_uuids from kg_vector_lookup table"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve embeddings and kg_uuids: {e}")
            raise Exception(f"Failed to retrieve embeddings and kg_uuids: {e}")

    async def vector_similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:

        if not self.pool:
            await self.initialize()

        try:
            # Using cosine distance operator (<=>) from pgvector
            # 1 - cosine_distance = cosine_similarity
            # We order by cosine distance ascending (closest first)
            query = """
                SELECT
                    kg_uuid,
                    missing_part,
                    document_id,
                    1 - (embedding <=> $1) as similarity_score
                FROM kg_vector_lookup
                WHERE 1 - (embedding <=> $1) >= $2
                ORDER BY embedding <=> $1 ASC
                LIMIT $3
            """

            result = await self.execute_query(
                query, [query_embedding, similarity_threshold, limit]
            )

            logger.info(
                f"Found {len(result)} similar vectors with threshold {similarity_threshold}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to perform vector similarity search: {e}")
            raise Exception(f"Failed to perform vector similarity search: {e}")
