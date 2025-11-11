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
    
    # Build label filter for person_type
    if person_type and person_type.lower() == 'citizen':
        label_filter = "AND 'Citizen' IN labels(ego)"
    elif person_type and person_type.lower() == 'resident':
        label_filter = "AND 'Resident' IN labels(ego)"
    else:
        label_filter = ""

    cypher = f"""
    MATCH (ego)
    WHERE (ego:Citizen OR ego:Resident) 
      AND ego.spm_person_no = $id
      {label_filter}
    
    WITH ego
    WHERE ego IS NOT NULL

    // 5-tier nodes
    OPTIONAL MATCH (ego)-[:SPOUSE_OF]-(sp)
    WHERE sp:Citizen OR sp:Resident
    
    OPTIONAL MATCH (ego)-[:CHILD_OF*1..{up_hops}]->(anc)
    WHERE anc:Citizen OR anc:Resident
    
    OPTIONAL MATCH (ego)<-[:CHILD_OF*1..{down_hops}]-(desc)
    WHERE desc:Citizen OR desc:Resident
    
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(p)<-[:CHILD_OF]-(sib)
    WHERE (sib:Citizen OR sib:Resident) AND sib <> ego

    WITH ego,
         collect(DISTINCT sp)   AS spouses,
         collect(DISTINCT anc)  AS ancestors,
         collect(DISTINCT desc) AS descendants,
         collect(DISTINCT sib)  AS siblings

    // Combine all nodes, ensuring ego is included
    WITH ego, spouses, ancestors, descendants, siblings,
         [n IN ([ego] + spouses + ancestors + descendants + siblings) WHERE n IS NOT NULL] AS all_nodes
    
    WITH ego, all_nodes,
         [n IN all_nodes | n.spm_person_no] AS node_ids

    // Get child edges
    UNWIND all_nodes AS child
    OPTIONAL MATCH (child)-[:CHILD_OF]->(parent)
    WHERE parent IN all_nodes
    WITH ego, all_nodes, collect(DISTINCT {{
        source: child.spm_person_no,
        target: parent.spm_person_no,
        type: 'CHILD_OF'
    }}) AS child_edges

    // Get spouse edges (deduplicated)
    UNWIND all_nodes AS person1
    OPTIONAL MATCH (person1)-[:SPOUSE_OF]-(person2)
    WHERE person2 IN all_nodes AND person1.spm_person_no < person2.spm_person_no
    WITH ego, all_nodes, child_edges, collect(DISTINCT {{
        source: person1.spm_person_no,
        target: person2.spm_person_no,
        type: 'SPOUSE_OF'
    }}) AS spouse_edges

    WITH ego, all_nodes, 
         [e IN child_edges WHERE e.source IS NOT NULL AND e.target IS NOT NULL] +
         [e IN spouse_edges WHERE e.source IS NOT NULL AND e.target IS NOT NULL] AS edges

    // Resolve father/mother for kinship computation
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(father)
    WHERE father IN all_nodes AND father.sex = 'M'
    
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(mother)
    WHERE mother IN all_nodes AND mother.sex = 'F'

    WITH ego, all_nodes, edges, 
         head(collect(DISTINCT father)) AS father, 
         head(collect(DISTINCT mother)) AS mother

    // Build node objects with kinship
    UNWIND all_nodes AS n
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

    // Determine person_type from labels
    WITH ego, edges, n, kin,
         CASE 
           WHEN 'Citizen' IN labels(n) THEN 'citizen'
           WHEN 'Resident' IN labels(n) THEN 'resident'
           ELSE 'unknown'
         END AS person_type

    WITH ego, edges, collect({{
      id: n.spm_person_no,
      label: coalesce(n.full_name, n.spm_person_no),
      full_name: n.full_name,
      sex: n.sex,
      date_of_birth: CASE WHEN n.spm_dob IS NOT NULL THEN toString(n.spm_dob) ELSE null END,
      national_id: n.national_id,
      passport: n.passport,
      person_type: person_type,
      kin: kin
    }}) AS nodes

    RETURN ego.spm_person_no AS root_id, nodes, edges
    """

    rows = neo4j_client.run(cypher, {"id": spm_person_no})
    if not rows or not rows[0]:
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
    MATCH (a) WHERE (a:Citizen OR a:Resident) AND a.spm_person_no = $p1
    MATCH (b) WHERE (b:Citizen OR b:Resident) AND b.spm_person_no = $p2
    MATCH pathA = (a)-[:CHILD_OF*0..]->(anc)
    WHERE anc:Citizen OR anc:Resident
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