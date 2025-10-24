from neo4j import GraphDatabase
import json
import trino

NEO4J_URI = "http://localhost:7474"
NEO4J_USER = "neo4j"
NEO4J_PASS = "neo4jneo4j"

TRINO_HOST="trino-svc"
TRINO_PORT=8080
TRINO_CATALOG="lake"
TRINO_SCHEMA="gold"

def upsert_graph(session, ego_json_str):
    ego = json.loads(ego_json_str)
    nodes = ego["nodes"]; edges = ego["edges"]
    for n in nodes:
        session.run("""
            MERGE (p:Person {entity_person_id:$id})
            SET p.full_name=$label, p.sex=$sex
        """, id=n["id"], label=n.get("label"), sex=n.get("sex"))
    for e in edges:
        if e["type"] == "CHILD_OF":
            session.run("""
                MATCH (c:Person {entity_person_id:$c}), (p:Person {entity_person_id:$p})
                MERGE (c)-[:CHILD_OF]->(p)
            """, c=e["source"], p=e["target"])
        elif e["type"] == "SPOUSE_OF":
            session.run("""
                MATCH (a:Person {entity_person_id:$a}), (b:Person {entity_person_id:$b})
                MERGE (a)-[:SPOUSE_OF]->(b)
            """, a=e["source"], b=e["target"])

def main(limit=100):
    conn = trino.dbapi.connect(
        host=TRINO_HOST, port=TRINO_PORT, user="airflow",
        catalog=TRINO_CATALOG, schema=TRINO_SCHEMA
    )
    cur = conn.cursor()
    cur.execute("SELECT ego_json FROM ego3_cache ORDER BY generated_at DESC LIMIT %s" % limit)
    rows = cur.fetchall()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        for (ego_json,) in rows:
            upsert_graph(session, ego_json)

if __name__ == "__main__":
    main()
