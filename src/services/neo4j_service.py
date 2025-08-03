"""
Neo4j Service for Knowledge Graph Storage

Handles connection to Neo4j and provides methods to insert triples.
"""

from neo4j import GraphDatabase
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# TODO: create script for importing ttl data, don't just run it and comment it out.


class Neo4jService:
    def __init__(self):
        return
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "samvidneo4j")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Connected to Neo4j at {uri} as {user}")

        # Import initial data from TTL file
        # try:
        #     self.import_ttl_data("sunworld_test_data/kg_data.ttl")
        #     logger.info("Sucessfully imported synthetic KG data")
        # except Exception as e:
        #     logger.error(f"Failed to import initial KG data: {e}")

        # self.test_connection_and_data()

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
        tx.run(
            query,
            subject=triple["subject"],
            predicate=triple["predicate"],
            object=triple["object"],
            confidence=triple.get("confidence", 1.0),
            source=triple.get("source", "unknown"),
        )

    async def run_cypher_query(
        self, query: str, parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Runs a Cypher query and returns the results."""
        if parameters is None:
            parameters = {}
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def import_ttl_data(self, ttl_file_path: str):
        """Imports data from a TTL file into Neo4j."""
        try:
            from rdflib import Graph

            g = Graph()
            g.parse(ttl_file_path, format="turtle")

            triples_to_insert = []
            for s, p, o in g:
                # Convert RDFLib URIs/Literals to strings for Neo4j
                subject = str(s)
                predicate = str(p)
                obj = str(o)

                triples_to_insert.append(
                    {
                        "subject": subject,
                        "predicate": predicate,
                        "object": obj,
                        "confidence": 1.0,  # Default confidence for imported data
                        "source": ttl_file_path,
                    }
                )

            if triples_to_insert:
                self.insert_triples(triples_to_insert)
                logger.info(
                    f"Successfully imported {len(triples_to_insert)} triples from {ttl_file_path}"
                )
            else:
                logger.info(f"No triples found in {ttl_file_path} to import.")

        except ImportError:
            logger.error(
                "rdflib is not installed. Please install it: pip install rdflib"
            )
            raise
        except Exception as e:
            logger.error(f"Error importing TTL data from {ttl_file_path}: {e}")
            raise

    def test_connection_and_data(self):
        """Tests the Neo4j connection and prints a sample of imported data."""
        try:
            query = "MATCH (s)-[r]->(o) RETURN s.name, type(r), o.name LIMIT 10"
            results = self.run_cypher_query(query)
            if results:
                logger.info("\n--- Neo4j Sample Data ---")
                for record in results:
                    logger.info(
                        f"Subject: {record.get('s.name')}, Predicate: {record.get('type(r)')}, Object: {record.get('o.name')}"
                    )
                logger.info("--- End Neo4j Sample Data ---\n")
            else:
                logger.info("No data found in Neo4j after import.")
        except Exception as e:
            logger.error(f"Error testing Neo4j connection or data: {e}")
