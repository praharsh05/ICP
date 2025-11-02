from typing import Dict, Any, Optional
from app.db.neo4j_client import neo4j_client

def get_person_tree(
    spm_person_no: str, 
    depth: int = 3,
    person_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    5-tier tree for the Sigma UI with optional person_type filtering.
    
    Includes:
      - ego
      - spouses (1 hop)
      - parents & grandparents (up to 2 hops up)
      - children & grandchildren (up to 2 hops down)
      - siblings (share >=1 parent)
    
    Emits only directed CHILD_OF (child -> parent) and deduped SPOUSE_OF.
    
    Args:
        spm_person_no: Root person ID
        depth: Tree depth (capped at 5 tiers: max 2 up, 2 down)
        person_type: Optional filter - 'citizen' or 'resident'
        
    Returns:
        Dict with root, nodes (with full metadata), and edges
    """
    # Cap to 5 tiers: max 2 up, 2 down
    up_hops = min(2, max(0, depth - 1))
    down_hops = min(2, max(0, depth - 1))
    
    # Build WHERE clause for person_type filter
    # Only filter if person_type is explicitly provided and valid
    type_filter = ""
    if person_type and person_type.lower() in ['citizen', 'resident']:
        type_filter = f"AND ego.person_type = '{person_type.lower()}'"

    cypher = f"""
    MATCH (ego:Person {{spm_person_no: $id}})
    WHERE 1=1 {type_filter}

    // 5-tier nodes
    OPTIONAL MATCH (ego)-[:SPOUSE_OF]-(sp:Person)
    OPTIONAL MATCH (ego)-[:CHILD_OF*1..{up_hops}]->(anc:Person)          // parents, grandparents
    OPTIONAL MATCH (ego)<-[:CHILD_OF*1..{down_hops}]-(desc:Person)       // children, grandchildren
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(p:Person)<-[:CHILD_OF]-(sib:Person)
    WHERE sib <> ego

    WITH ego,
         collect(DISTINCT sp)   AS spouses,
         collect(DISTINCT anc)  AS ancestors,
         collect(DISTINCT desc) AS descendants,
         collect(DISTINCT sib)  AS siblings

    WITH ego,
            [ego] + spouses + ancestors + descendants + siblings AS ns
    UNWIND ns AS n
    WITH ego, collect(DISTINCT n) AS nodes

    // directed edges among nodes
    // child -> parent
    UNWIND nodes AS c
    MATCH (c)-[:CHILD_OF]->(p)
    WHERE p IN nodes
    WITH ego, nodes,
         collect(DISTINCT {{
           source: c.spm_person_no,
           target: p.spm_person_no,
           type: 'CHILD_OF'
         }}) AS child_edges

    UNWIND nodes AS a
    MATCH (a)-[:SPOUSE_OF]-(b)
    WHERE b IN nodes AND a.spm_person_no < b.spm_person_no
    WITH ego, nodes, child_edges,
        collect(DISTINCT {{
            source: a.spm_person_no,
            target: b.spm_person_no,
            type: 'SPOUSE_OF'
        }}) AS spouse_edges

    WITH ego, nodes, (child_edges + spouse_edges) AS edges

    // resolve father/mother if present
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(fa:Person {{sex:'M'}})
    WHERE fa IN nodes
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(mo:Person {{sex:'F'}})
    WHERE mo IN nodes
    WITH ego, nodes, edges, head(collect(DISTINCT fa)) AS father, head(collect(DISTINCT mo)) AS mother

    // compute kin (gender-specific where possible)
    UNWIND nodes AS n
    WITH ego, father, mother, n, edges
    WITH ego, father, mother, n, edges,
         CASE
           WHEN n = ego THEN 'self'

           WHEN (n)-[:SPOUSE_OF]-(ego) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'husband'
               WHEN 'F' THEN 'wife'
               ELSE 'spouse'
             END

           WHEN (ego)-[:CHILD_OF]->(n) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'father'
               WHEN 'F' THEN 'mother'
               ELSE 'parent'
             END

           WHEN (n)-[:CHILD_OF]->(ego) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'son'
               WHEN 'F' THEN 'daughter'
               ELSE 'child'
             END

           WHEN (ego)-[:CHILD_OF]->()<-[:CHILD_OF]-(n) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'brother'
               WHEN 'F' THEN 'sister'
               ELSE 'sibling'
             END

           WHEN father IS NOT NULL AND (father)-[:CHILD_OF]->(n) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'paternal grandfather'
               WHEN 'F' THEN 'paternal grandmother'
               ELSE 'paternal grandparent'
             END

           WHEN mother IS NOT NULL AND (mother)-[:CHILD_OF]->(n) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'maternal grandfather'
               WHEN 'F' THEN 'maternal grandmother'
               ELSE 'maternal grandparent'
             END

           WHEN (n)-[:CHILD_OF]->()<-[:CHILD_OF]-(ego) THEN
             CASE toUpper(n.sex)
               WHEN 'M' THEN 'grandson'
               WHEN 'F' THEN 'granddaughter'
               ELSE 'grandchild'
             END

           ELSE ''
         END AS kin

    WITH ego, edges, collect(DISTINCT {{
      id: n.spm_person_no,
      label: coalesce(n.full_name, n.name, n.spm_person_no),
      full_name: n.full_name,
      sex: n.sex,
      date_of_birth: toString(n.dob),
      national_id: n.national_id,
      passport: n.passport,
      person_type: n.person_type,
      kin: kin
    }}) AS node_maps

    RETURN ego, node_maps AS nodes, edges
    """

    rows = neo4j_client.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}

    rec = rows[0]
    return {
        "root": spm_person_no,
        "nodes": rec["nodes"] or [],
        "edges": rec["edges"] or [],
    }

def lowest_common_ancestors(p1: str, p2: str, limit: int = 5):
    """
    LCA over biological graph = CHILD_OF upward only.
    Returns up to `limit` ancestors with minimal combined depth.
    
    Args:
        p1: First person ID
        p2: Second person ID
        limit: Maximum number of ancestors to return
        
    Returns:
        List of common ancestors with depth information
    """
    cypher = """
    MATCH (a:Person {spm_person_no:$p1}), (b:Person {spm_person_no:$p2})
    MATCH pathA = (a)-[:CHILD_OF*0..]->(anc:Person)
    WITH b, anc, length(pathA) AS da
    MATCH pathB = (b)-[:CHILD_OF*0..]->(anc)
    WITH anc, da, length(pathB) AS db
    RETURN anc.spm_person_no AS ancestor_id,
           anc.full_name     AS full_name,
           da, db, (da+db)   AS total_depth
    ORDER BY total_depth ASC, da ASC, db ASC
    LIMIT $limit
    """
    rows = neo4j_client.run(cypher, {"p1": p1, "p2": p2, "limit": limit})
    return [dict(r) for r in rows]
