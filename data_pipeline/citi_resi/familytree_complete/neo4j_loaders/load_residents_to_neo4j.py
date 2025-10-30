"""
Load Residents data from Trino to Neo4j
"""
from neo4j import GraphDatabase
import trino
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = "residents"

TRINO_HOST = os.getenv("TRINO_HOST", "trino-svc")
TRINO_PORT = int(os.getenv("TRINO_PORT", 8080))

def main():
    print("Loading Residents to Neo4j...")
    
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user="airflow",
        catalog="lake",
        schema="silver"
    )
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    
    with driver.session(database=NEO4J_DATABASE) as session:
        # Create indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.entity_person_id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.spm_person_no)")
        
        # Load persons (simplified)
        cur = conn.cursor()
        cur.execute("SELECT entity_person_id, primary_spm_person_no, full_name, sex FROM residents_person_entity LIMIT 1000")
        
        batch = []
        for row in cur.fetchall():
            batch.append({
                "entity_person_id": row[0],
                "spm_person_no": row[1],
                "full_name": row[2],
                "sex": row[3],
                "person_type": "resident"
            })
        
        if batch:
            session.run("""
                UNWIND $batch AS person
                MERGE (p:Resident:Person {entity_person_id: person.entity_person_id})
                SET p.spm_person_no = person.spm_person_no,
                    p.full_name = person.full_name,
                    p.sex = person.sex,
                    p.person_type = person.person_type
            """, batch=batch)
            print(f"✓ Loaded {len(batch)} persons")
    
    driver.close()
    conn.close()
    print("✓ Residents data loaded to Neo4j")

if __name__ == "__main__":
    main()
