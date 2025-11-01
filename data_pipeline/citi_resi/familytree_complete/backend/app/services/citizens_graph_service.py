"""
Citizens Graph Service
"""
from typing import Dict, Any, List
from app.db.neo4j_client import citizens_neo4j

def get_person_tree(spm_person_no: str, depth: int = 3, lang: str = "en") -> Dict[str, Any]:
    """Get family tree for a citizen"""
    
    cypher = f"""
    MATCH (ego:Citizen {{spm_person_no: $id}})
    
    OPTIONAL MATCH (ego)-[:CHILD_OF*1..{depth-1}]->(anc:Citizen)
    OPTIONAL MATCH (ego)<-[:CHILD_OF*1..{depth-1}]-(desc:Citizen)
    OPTIONAL MATCH (ego)-[:SPOUSE_OF]-(sp:Person)
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(p:Citizen)<-[:CHILD_OF]-(sib:Citizen)
    WHERE sib <> ego
    
    WITH ego, [ego] + collect(DISTINCT anc) + collect(DISTINCT desc) + 
         collect(DISTINCT sp) + collect(DISTINCT sib) AS all_nodes
    UNWIND all_nodes AS n
    WITH ego, collect(DISTINCT n) AS nodes
    
    UNWIND nodes AS c
    OPTIONAL MATCH (c)-[:CHILD_OF]->(p:Person)
    WHERE p IN nodes
    WITH ego, nodes, collect(DISTINCT {{
        source: c.spm_person_no,
        target: p.spm_person_no,
        type: 'CHILD_OF'
    }}) AS child_edges
    
    UNWIND nodes AS a
    OPTIONAL MATCH (a)-[:SPOUSE_OF]-(b:Person)
    WHERE b IN nodes AND a.spm_person_no < b.spm_person_no
    WITH ego, nodes, child_edges, collect(DISTINCT {{
        source: a.spm_person_no,
        target: b.spm_person_no,
        type: 'SPOUSE_OF'
    }}) AS spouse_edges
    
    WITH ego, nodes, (child_edges + spouse_edges) AS edges
    
    UNWIND nodes AS n
    RETURN ego, collect({{
      id: n.spm_person_no,
      entity_id: n.entity_person_id,
      label: coalesce(n.full_name, n.spm_person_no),
      sex: n.sex,
      person_type: n.person_type,
      kin: CASE
        WHEN n = ego THEN 'self'
        WHEN (n)-[:SPOUSE_OF]-(ego) THEN 'spouse'
        WHEN (ego)-[:CHILD_OF]->(n) THEN 'parent'
        WHEN (n)-[:CHILD_OF]->(ego) THEN 'child'
        ELSE 'relative'
      END
    }}) AS nodes, edges
    """
    
    rows = citizens_neo4j.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}
    
    rec = rows[0]
    return {
        "root": spm_person_no,
        "nodes": rec["nodes"] or [],
        "edges": rec["edges"] or [],
        "person_type": "citizen"
    }

def lowest_common_ancestors(p1: str, p2: str, limit: int = 5) -> List[Dict]:
    """Find lowest common ancestors"""
    cypher = """
    MATCH (a:Citizen {spm_person_no:$p1}), (b:Citizen {spm_person_no:$p2})
    MATCH pathA = (a)-[:CHILD_OF*0..10]->(anc:Citizen)
    WITH b, anc, length(pathA) AS da
    MATCH pathB = (b)-[:CHILD_OF*0..10]->(anc)
    RETURN anc.spm_person_no AS ancestor_id,
           anc.full_name AS full_name,
           da, 
           length(pathB) AS db,
           (da + length(pathB)) AS total_depth
    ORDER BY total_depth ASC
    LIMIT $limit
    """
    
    rows = citizens_neo4j.run(cypher, {"p1": p1, "p2": p2, "limit": limit})
    return [dict(r) for r in rows]
