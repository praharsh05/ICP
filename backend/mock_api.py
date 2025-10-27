
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any
import time

app = FastAPI(title="FamilyTree API (Mock)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

NOW = time.time()
MOCK_GRAPH = {
    "E1": {
        "root": "E1",
        "nodes": [
            {"id":"E1","label":"Ali Hassan","sex":"M","kin":"self","cluster":None},
            {"id":"E2","label":"Hassan Ibrahim","sex":"M","kin":"father","cluster":"ancestors"},
            {"id":"E3","label":"Mariam Saeed","sex":"F","kin":"mother","cluster":"ancestors"},
            {"id":"E4","label":"Aisha Ali","sex":"F","kin":"spouse","cluster":"inlaws"},
            {"id":"E5","label":"Omar Ali","sex":"M","kin":"son","cluster":"descendants"},
            {"id":"E6","label":"Laila Ali","sex":"F","kin":"daughter","cluster":"descendants"},
            {"id":"E7","label":"Fatima Hassan","sex":"F","kin":"sister","cluster":None}
        ],
        "edges": [
            {"source":"E1","target":"E2","type":"CHILD_OF"},
            {"source":"E1","target":"E3","type":"CHILD_OF"},
            {"source":"E5","target":"E1","type":"CHILD_OF"},
            {"source":"E6","target":"E1","type":"CHILD_OF"},
            {"source":"E7","target":"E2","type":"CHILD_OF"},
            {"source":"E1","target":"E4","type":"SPOUSE_OF"},
            {"source":"E4","target":"E1","type":"SPOUSE_OF"}
        ],
        "generated_at": NOW
    }
}

@app.get("/api/v1/persons/{person_id}/tree")
def get_tree(person_id: str, depth: int = 3, lang: str = "en"):
    data = MOCK_GRAPH.get(person_id)
    if not data:
        return {"root": person_id, "nodes": [], "edges": [], "generated_at": time.time()}
    return data

@app.get("/api/v1/lca")
def lca(personA: str, personB: str):
    # MOCK only
    return {"lcas": ["E2"] if personA == "E1" and personB == "E7" else []}

@app.post("/api/v1/infer")
def infer(payload: Dict[str, Any]):
    pid = payload.get("person_id")
    return {"person_id": pid, "candidates": [{"type":"parent","target":"E2","score":0.76,"explanation":"Shared surname + age gap"}]}
