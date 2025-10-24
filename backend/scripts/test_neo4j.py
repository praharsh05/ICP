
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv("backend/.env")

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")
db = os.getenv("NEO4J_DATABASE", "neo4j")

print("URI: ", uri)
print("USer: ", user)
print("DB: ", db)
# auth = (user, password) if (user or password) else None
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as s:
    print(s.run("RETURN 1 AS ok").single())
driver.close()