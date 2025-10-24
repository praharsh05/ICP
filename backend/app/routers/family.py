from fastapi import APIRouter, HTTPException, Query
from app.services.graph_service import get_person_tree, lowest_common_ancestors

router = APIRouter(prefix="/api/v1", tags=["family"])

@router.get("/persons/{spm_person_no}/tree")
def read_tree(spm_person_no: str, depth: int = Query(3, ge=1, le=5), lang: str = "en"):
    data = get_person_tree(spm_person_no, depth=depth)
    if not data["nodes"]:
        # still return empty result so UI can show "No nodes"
        return data
    return data

@router.get("/lca")
def read_lca(p1: str, p2: str, limit: int = Query(5, ge=1, le=20)):
    if p1 == p2:
        # same person, LCA is the person with depth 0 total
        return [{"ancestor_id": p1, "full_name": None, "da": 0, "db": 0, "total_depth": 0}]
    res = lowest_common_ancestors(p1, p2, limit=limit)
    return res