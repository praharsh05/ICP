from typing import Dict, Any
from app.db.neo4j_client import neo4j_client

def get_person_tree(spm_person_no: str, depth: int = 3) -> Dict[str, Any]:
    """
    5-tier tree for the Sigma UI.
    Includes:
      - ego
      - spouses (1 hop)
      - parents & grandparents (up to 2 hops up)
      - children & grandchildren (up to 2 hops down)
      - siblings (share >=1 parent)
    Emits only directed CHILD_OF (child -> parent) and deduped SPOUSE_OF.
    """
    # cap to 5 tiers: max 2 up, 2 down
    up_hops = min(2, max(0, depth - 1))
    down_hops = min(2, max(0, depth - 1))

    cypher = f"""
    MATCH (ego:Person {{spm_person_no: $id}})

    // ----- collect neighborhood nodes -----
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

    // ----- build directed edges only among 'nodes' -----

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

    // spouses (dedup by internal id so we don't return both directions)
    UNWIND nodes AS a
    MATCH (a)-[:SPOUSE_OF]-(b)
    WHERE b IN nodes AND id(a) < id(b)
    WITH ego, nodes, child_edges,
         collect(DISTINCT {{
           source: a.spm_person_no,
           target: b.spm_person_no,
           type: 'SPOUSE_OF'
         }}) AS spouse_edges

    RETURN
      ego,
      nodes,
      child_edges + spouse_edges AS edges
    """

    rows = neo4j_client.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}

    rec = rows[0]
    ego = rec["ego"]
    nodes = rec["nodes"] or []
    edges = rec["edges"] or []

    # Build UI-friendly node objects
    unique = {}
    def add_node(n, kin=None):
        if not n:
            return
        pid = n.get("spm_person_no")
        if not pid:
            return
        if pid not in unique:
            unique[pid] = {
                "id": pid,
                "label": n.get("full_name") or n.get("name") or pid,
                "sex": n.get("sex"),
                "kin": kin or ("self" if ego and pid == ego.get("spm_person_no") else ""),
            }
        elif kin and not unique[pid].get("kin"):
            unique[pid]["kin"] = kin

    for n in nodes:
        # mark ego explicitly
        if ego and n.get("spm_person_no") == ego.get("spm_person_no"):
            add_node(n, kin="self")
        else:
            add_node(n)

    return {
        "root": spm_person_no,
        "nodes": list(unique.values()),
        "edges": edges,  # already directed & deduped by Cypher above
    }

def lowest_common_ancestors(p1: str, p2: str, limit: int = 5):
    """
    LCA over biological graph = CHILD_OF upward only.
    Returns up to `limit` ancestors with minimal combined depth.
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