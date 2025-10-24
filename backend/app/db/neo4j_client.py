import os
from neo4j import GraphDatabase, Driver
from typing import Optional

class Neo4jClient:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def connect(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def run(self, cypher: str, params: dict = None, db: Optional[str] = None):
        if self._driver is None:
            self.connect()
        database = db or os.getenv("NEO4J_DB", "neo4j")
        with self._driver.session(database=database) as session:
            return list(session.run(cypher, params or {}))

neo4j_client = Neo4jClient()