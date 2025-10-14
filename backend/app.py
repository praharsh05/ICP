from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
from datetime import date
import os, base64, json
from neo4j import GraphDatabase, basic_auth

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

app = FastAPI(title="Family Graph Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def enc_cursor(offset:int)->str:
    return base64.urlsafe_b64encode(json.dumps({"o":offset}).encode()).decode()

def dec_cursor(cur:Optional[str])->int:
    if not cur: return 0
    try:
        return int(json.loads(base64.urlsafe_b64decode(cur.encode()).decode()).get("o",0))
    except Exception:
        return 0

PEOPLE = {"U1":{"uid":"U1","full_name_en":"Alex Center","counts":{"parents":2,"children":22,"spouses":1,"siblings":18}}}
for i in range(22):
    pid=f"U2C{i:02d}"; PEOPLE[pid]={"uid":pid,"full_name_en":f"Child #{i}","counts":{"children":0,"spouses":0}}
for i in range(18):
    pid=f"U2S{i:02d}"; PEOPLE[pid]={"uid":pid,"full_name_en":f"Sibling #{i}","counts":{"children":0 if i%3 else 1,"spouses":1 if i%4==0 else 0}}
PEOPLE.update({
 "U10":{"uid":"U10","full_name_en":"Parent One","counts":{"children":3,"spouses":1}},
 "U11":{"uid":"U11","full_name_en":"Parent Two","counts":{"children":3,"spouses":1}},
 "U2":{"uid":"U2","full_name_en":"Spouse A","counts":{"children":2,"spouses":1}},
 "U20":{"uid":"U20","full_name_en":"Child A","counts":{"children":0,"spouses":0}},
 "U21":{"uid":"U21","full_name_en":"Child B","counts":{"children":0,"spouses":0}},
 "U30":{"uid":"U30","full_name_en":"Sibling A","counts":{"children":1,"spouses":1}},
 "U31":{"uid":"U31","full_name_en":"Sibling B","counts":{"children":0,"spouses":0}},
 "U32":{"uid":"U32","full_name_en":"Sibling C","counts":{"children":2,"spouses":1}},
})

def mock_page(lst, limit:int, cursor:str):
    off = dec_cursor(cursor)
    page = lst[off:off+limit]
    nxt = off + len(page)
    has_more = nxt < len(lst)
    return page, len(lst), has_more, (enc_cursor(nxt) if has_more else None)

def mock_neighborhood(uid:str, limit:int, as_of:Optional[date], cursors:Dict[str,str]):
    center = PEOPLE.get(uid, {"uid":uid,"full_name_en":f"Person {uid}","counts":{"parents":0,"children":0,"spouses":0,"siblings":0}})
    parents_all  = [PEOPLE["U10"], PEOPLE["U11"]]
    children_all = [PEOPLE["U20"], PEOPLE["U21"]] + [PEOPLE[f"U2C{i:02d}"] for i in range(22)]
    siblings_all = [PEOPLE["U30"], PEOPLE["U31"], PEOPLE["U32"]] + [PEOPLE[f"U2S{i:02d}"] for i in range(18)]
    spouses_all  = [PEOPLE["U2"]] if uid=="U1" else ([PEOPLE["U1"]] if uid=="U2" else [])
    ch, ch_tot, ch_more, ch_next = mock_page(children_all, limit, cursors.get("children"))
    sib, sib_tot, sib_more, sib_next = mock_page(siblings_all, limit, cursors.get("siblings"))
    par, par_tot, par_more, par_next = mock_page(parents_all, limit, cursors.get("parents"))
    sp, sp_tot, sp_more, sp_next = mock_page(spouses_all, limit, cursors.get("spouses"))
    return {"center":center,
            "parents":{"items":par,"total":par_tot,"hasMore":par_more,"nextCursor":par_next},
            "children":{"items":ch,"total":ch_tot,"hasMore":ch_more,"nextCursor":ch_next},
            "spouses":{"items":sp,"total":sp_tot,"hasMore":sp_more,"nextCursor":sp_next},
            "siblings":{"items":sib,"total":sib_tot,"hasMore":sib_more,"nextCursor":sib_next}}

def neo4j_driver():
    return GraphDatabase.driver(os.getenv("NEO4J_URI","neo4j://localhost:7687"),
                                auth=basic_auth(os.getenv("NEO4J_USER","neo4j"),
                                                os.getenv("NEO4J_PASSWORD","password")))

CYPHER_NEIGHBORHOOD = '''
MATCH (c:Person {uid:$uid})
WITH c
OPTIONAL MATCH (par:Person)-[:PARENT_OF]->(c)
WITH c, collect(par)[toInteger($parentsOffset)..toInteger($parentsOffset)+toInteger($limit)] AS parents,
     size((:Person)-[:PARENT_OF]->(c)) AS parents_total
OPTIONAL MATCH (c)-[:PARENT_OF]->(ch:Person)
WITH c, parents, parents_total,
     collect(ch)[toInteger($childrenOffset)..toInteger($childrenOffset)+toInteger($limit)] AS children,
     size((c)-[:PARENT_OF]->(:Person)) AS children_total
OPTIONAL MATCH (c)-[sp:SPOUSE_OF]-(spm:Person)
WHERE $asOfDate IS NULL OR (sp.valid_from <= date($asOfDate) AND date($asOfDate) < sp.valid_to)
WITH c, parents, parents_total, children, children_total,
     collect(spm)[toInteger($spousesOffset)..toInteger($spousesOffset)+toInteger($limit)] AS spouses,
     size([(c)-[sp2:SPOUSE_OF]-(:Person) WHERE $asOfDate IS NULL OR (sp2.valid_from <= date($asOfDate) AND date($asOfDate) < sp2.valid_to) | sp2]) AS spouses_total
OPTIONAL MATCH (sibling:Person)-[:PARENT_OF]->(x)<-[:PARENT_OF]-(c)
WHERE sibling <> c
WITH c, parents, parents_total, children, children_total, spouses, spouses_total,
     collect(DISTINCT sibling)[toInteger($siblingsOffset)..toInteger($siblingsOffset)+toInteger($limit)] AS siblings,
     size(collect(DISTINCT sibling)) AS siblings_total
RETURN c AS center, parents, parents_total, children, children_total, spouses, spouses_total, siblings, siblings_total
'''

def counts_query():
    return '''
UNWIND $uids AS uid
MATCH (p:Person {uid: uid})
OPTIONAL MATCH (p)-[:PARENT_OF]->(c:Person)
WITH p, count(c) AS child_count
OPTIONAL MATCH (p)-[sp:SPOUSE_OF]-(:Person)
WHERE $asOfDate IS NULL OR (sp.valid_from <= date($asOfDate) AND date($asOfDate) < sp.valid_to)
RETURN p.uid AS uid, child_count, count(sp) AS spouse_count
'''

@app.get("/health")
def health(): return {"ok": True, "mock": MOCK_MODE}

@app.get("/person/{uid}/neighborhood")
def neighborhood(uid: str, asOfDate: Optional[date] = None, limit: int = 20,
                 cursor_parents: Optional[str] = None,
                 cursor_children: Optional[str] = None,
                 cursor_spouses: Optional[str] = None,
                 cursor_siblings: Optional[str] = None):
    cursors = {"parents": cursor_parents, "children": cursor_children, "spouses": cursor_spouses, "siblings": cursor_siblings}
    if MOCK_MODE:
        return mock_neighborhood(uid, limit, asOfDate, cursors)

    drv = neo4j_driver()
    as_of = str(asOfDate) if asOfDate else None
    with drv.session(default_access_mode="READ") as s:
        rec = s.run(CYPHER_NEIGHBORHOOD, uid=uid, limit=limit, asOfDate=as_of,
                    parentsOffset=dec_cursor(cursor_parents),
                    childrenOffset=dec_cursor(cursor_children),
                    spousesOffset=dec_cursor(cursor_spouses),
                    siblingsOffset=dec_cursor(cursor_siblings)).single()
        if not rec:
            return {"center":{"uid":uid,"full_name_en":f"Person {uid}","counts":{"parents":0,"children":0,"spouses":0,"siblings":0}},
                    "parents":{"items": [], "total": 0, "hasMore": False, "nextCursor": None},
                    "children":{"items": [], "total": 0, "hasMore": False, "nextCursor": None},
                    "spouses":{"items": [], "total": 0, "hasMore": False, "nextCursor": None},
                    "siblings":{"items": [], "total": 0, "hasMore": False, "nextCursor": None}}
        center = rec["center"]
        parents = rec["parents"] or []
        children = rec["children"] or []
        spouses = rec["spouses"] or []
        siblings = rec["siblings"] or []
        neighbor_uids = [p["uid"] for p in parents+children+spouses+siblings if p]
        counts_map = {}
        if neighbor_uids:
            cq = counts_query()
            for row in s.run(cq, uids=neighbor_uids, asOfDate=as_of):
                counts_map[row["uid"]] = {"children": row["child_count"], "spouses": row["spouse_count"]}
        def shape(items, total, key):
            off = dec_cursor(cursors[key]); nxt = off + len(items); has_more = nxt < total
            shaped = []
            for it in items:
                d = dict(it); d["counts"] = counts_map.get(it["uid"], {"children":0,"spouses":0}); shaped.append(d)
            return {"items": shaped, "total": total, "hasMore": has_more, "nextCursor": (enc_cursor(nxt) if has_more else None)}
        return {"center": dict(center),
                "parents": shape(parents, rec["parents_total"], "parents"),
                "children": shape(children, rec["children_total"], "children"),
                "spouses": shape(spouses, rec["spouses_total"], "spouses"),
                "siblings": shape(siblings, rec["siblings_total"], "siblings")}