"""
Residents Graph Service
"""
from typing import Dict, Any
from app.db.neo4j_client import residents_neo4j

def get_person_tree(spm_person_no: str, depth: int = 2) -> Dict[str, Any]:
    """Get sponsorship network for a resident"""
    
    cypher = f"""
    MATCH (ego:Resident {{spm_person_no: $id}})
    
    OPTIONAL MATCH path1 = (ego)-[:SPONSORED_BY*1..{depth}]->(sponsor:Person)
    OPTIONAL MATCH path2 = (ego)<-[:SPONSORED_BY*1..{depth}]-(sponsored:Resident)
    
    WITH ego, [ego] + collect(DISTINCT sponsor) + collect(DISTINCT sponsored) AS all_nodes
    UNWIND all_nodes AS n
    WITH ego, collect(DISTINCT n) AS nodes
    
    UNWIND nodes AS sponsored
    OPTIONAL MATCH (sponsored)-[r:SPONSORED_BY]->(sponsor:Person)
    WHERE sponsor IN nodes
    WITH ego, nodes, collect(DISTINCT {{
        source: sponsored.spm_person_no,
        target: sponsor.spm_person_no,
        type: 'SPONSORED_BY'
    }}) AS edges
    
    UNWIND nodes AS n
    RETURN ego, collect({{
      id: n.spm_person_no,
      entity_id: n.entity_person_id,
      label: coalesce(n.full_name, n.spm_person_no),
      sex: n.sex,
      person_type: n.person_type
    }}) AS nodes, edges
    """
    
    rows = residents_neo4j.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}
    
    rec = rows[0]
    return {
        "root": spm_person_no,
        "nodes": rec["nodes"] or [],
        "edges": rec["edges"] or [],
        "person_type": "resident"
    }

def get_sponsorship_family(sponsor_id: str) -> Dict[str, Any]:
    """Get all persons sponsored by a sponsor"""
    cypher = """
    MATCH (sponsor:Person {spm_person_no: $id})
    OPTIONAL MATCH (sponsor)<-[:SPONSORED_BY]-(sponsored:Resident)
    RETURN sponsor, collect({{
      id: sponsored.spm_person_no,
      label: coalesce(sponsored.full_name, sponsored.spm_person_no),
      sex: sponsored.sex
    }}) AS sponsored_persons
    """
    
    rows = residents_neo4j.run(cypher, {"id": sponsor_id})
    if not rows:
        return {"sponsor": sponsor_id, "sponsored": []}
    
    rec = rows[0]
    return {
        "sponsor": sponsor_id,
        "sponsored": rec["sponsored_persons"] or []
    }
