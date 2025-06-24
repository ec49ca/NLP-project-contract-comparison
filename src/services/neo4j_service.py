"""
Neo4j Service for Knowledge Graph Storage

Handles connection to Neo4j and provides methods to insert triples.
"""

from neo4j import GraphDatabase
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Connected to Neo4j at {uri} as {user}")

    def close(self):
        self.driver.close()

    def insert_triples(self, triples: List[Dict[str, Any]]):
        with self.driver.session() as session:
            for triple in triples:
                session.write_transaction(self._create_triple, triple)

    @staticmethod
    def _create_triple(tx, triple: Dict[str, Any]):
        # Cypher query to create nodes and relationship
        query = (
            "MERGE (s:Entity {name: $subject}) "
            "MERGE (o:Entity {name: $object}) "
            "MERGE (s)-[r:RELATION {type: $predicate}]->(o) "
            "SET r.confidence = $confidence, r.source = $source "
        )
        tx.run(query,
            subject=triple["subject"],
            predicate=triple["predicate"],
            object=triple["object"],
            confidence=triple.get("confidence", 1.0),
            source=triple.get("source", "unknown")
        )