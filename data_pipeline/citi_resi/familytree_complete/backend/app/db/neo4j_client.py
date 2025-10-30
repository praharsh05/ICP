"""
Neo4j Client for dual database support
"""
import os
from neo4j import GraphDatabase, Driver
from typing import Optional

class Neo4jClient:
    def __init__(self, database: str = "neo4j"):
        self._driver: Optional[Driver] = None
        self.database = database
    
    def connect(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def run(self, cypher: str, params: dict = None):
        if self._driver is None:
            self.connect()
        with self._driver.session(database=self.database) as session:
            return list(session.run(cypher, params or {}))

# Create clients for both databases
citizens_neo4j = Neo4jClient(database="citizens")
residents_neo4j = Neo4j Client(database="residents")
