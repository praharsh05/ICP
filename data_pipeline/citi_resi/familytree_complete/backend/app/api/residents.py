"""
Residents API Routes
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.residents_graph_service import get_person_tree, get_sponsorship_family

router = APIRouter()

@router.get("/persons/{spm_person_no}/tree")
def get_resident_tree(
    spm_person_no: str,
    depth: int = Query(2, ge=1, le=3)
):
    """Get sponsorship network for a resident"""
    try:
        data = get_person_tree(spm_person_no, depth=depth)
        if not data.get("nodes"):
            raise HTTPException(status_code=404, detail="Person not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sponsorship/{sponsor_id}/family")
def get_sponsored_family(sponsor_id: str):
    """Get all persons sponsored by this sponsor"""
    try:
        data = get_sponsorship_family(sponsor_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
