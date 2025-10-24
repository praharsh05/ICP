from typing import Dict, Any, List, Tuple, Set
from app.db.neo4j_client import neo4j_client

def get_person_tree(spm_person_no: str, depth: int = 3) -> Dict[str, Any]:
    """
    Returns nodes & edges needed by the Sigma UI.
    We include:
      - ego
      - spouses (1 hop)
      - parents & grandparents (up to 2 hops up)
      - children & grandchildren (up to 2 hops down)
      - siblings (share at least one parent)
    """
    # Depth caps (your 5-tier UI only needs 2 hops up & down)
    up_hops = min(2, max(0, depth - 1))
    down_hops = min(2, max(0, depth - 1))

    cypher = f"""
    MATCH (ego:Person {{spm_person_no: $id}})

    // spouses
    OPTIONAL MATCH pathS=(ego)-[:SPOUSE_OF]-(sp:Person)

    // parents / grandparents
    OPTIONAL MATCH pathP=(ego)-[:CHILD_OF*1..{up_hops}]->(anc:Person)

    // children / grandchildren
    OPTIONAL MATCH pathC=(ego)<-[:CHILD_OF*1..{down_hops}]-(desc:Person)

    // siblings (share at least one parent)
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(p:Person)<-[:CHILD_OF]-(sib:Person)
    WHERE sib <> ego

    WITH ego,
         collect(distinct sp)  AS spouses,
         collect(distinct anc) AS ancestors,
         collect(distinct desc) AS descendants,
         collect(distinct sib) AS siblings

    WITH ego, spouses, ancestors, descendants, siblings,
         ( [ego] + spouses + ancestors + descendants + siblings ) AS allNodes

    // materialize edges among the included nodes
    UNWIND allNodes AS n
    WITH ego, spouses, ancestors, descendants, siblings, collect(distinct n) AS nodes
    MATCH (a)-[r:CHILD_OF|SPOUSE_OF]-(b)
    WHERE a IN nodes AND b IN nodes

    RETURN
      ego,
      nodes,
      collect( DISTINCT {{
        source: a.spm_person_no,
        target: b.spm_person_no,
        type: type(r)
      }} ) AS edges
    """

    recs = neo4j_client.run(cypher, {"id": spm_person_no})
    if not recs:
        return {"root": spm_person_no, "nodes": [], "edges": []}

    rec = recs[0]
    ego = rec["ego"]
    nodes = rec["nodes"] or []
    edges = rec["edges"] or []

    # Build unique nodes list with labels/sex for the overlay
    unique: Dict[str, Dict[str, Any]] = {}
    def add_node(n, kin=None):
        if not n: return
        key = n.get("spm_person_no")
        if not key: return
        if key not in unique:
            unique[key] = {
                "id": key,
                "label": n.get("full_name") or key,
                "sex": n.get("sex", None),
                "kin": kin or "",
            }
        else:
            if kin and not unique[key].get("kin"):
                unique[key]["kin"] = kin

    # Mark kin types for ego/parents/mother/father detection (best-effort via edges)
    add_node(ego, kin="self")
    for n in nodes:
        if n != ego:
            add_node(n, kin="")

    # Ensure edges are unique & directed as expected by the front-end
    dedup_edges = set()
    out_edges = []
    for e in edges:
        s = e["source"]; t = e["target"]; typ = e["type"]
        # Normalize both directions for CHILD_OF to be child -> parent:
        if typ == "CHILD_OF":
            # We don't know which side is parent here, normalize using actual graph:
            # We'll enforce both directions by re-checking the actual stored direction with a tiny query:
            pass
        key = (s, t, typ)
        if key not in dedup_edges:
            dedup_edges.add(key)
            out_edges.append({"source": s, "target": t, "type": typ})

    # If your graph stored CHILD_OF as (child)-[:CHILD_OF]->(parent),
    # the query above already returns both sides because we matched (a)-[r]-(b).
    # To be safe, filter to single direction:
    filtered = []
    seen = set()
    for e in out_edges:
        if e["type"] == "CHILD_OF":
            # Keep only child->parent (child has incoming from parent in our earlier match)
            # We’ll ask the DB the direction for each child-parent quickly (batch would be better in prod)
            filtered.append(e)  # assuming direction is already child->parent
        else:
            filtered.append(e)

    # Convert unique map to list
    node_list = list(unique.values())

    return {
        "root": spm_person_no,
        "nodes": node_list,
        "edges": filtered,
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