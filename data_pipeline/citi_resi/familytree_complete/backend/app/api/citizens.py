"""
Citizens API Routes
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.citizens_graph_service import get_person_tree, lowest_common_ancestors

router = APIRouter()

@router.get("/persons/{spm_person_no}/tree")
def get_citizen_tree(
    spm_person_no: str,
    depth: int = Query(3, ge=1, le=5),
    lang: str = Query("en", regex="^(en|ar)$")
):
    """Get family tree for a citizen"""
    try:
        data = get_person_tree(spm_person_no, depth=depth, lang=lang)
        if not data.get("nodes"):
            raise HTTPException(status_code=404, detail="Person not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lca")
def get_lca(
    p1: str,
    p2: str,
    limit: int = Query(5, ge=1, le=20)
):
    """Get lowest common ancestors between two citizens"""
    if p1 == p2:
        return [{"ancestor_id": p1, "da": 0, "db": 0, "total_depth": 0}]
    
    try:
        result = lowest_common_ancestors(p1, p2, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
