"""
Unified API Routes (works for both citizens and residents)
"""
from fastapi import APIRouter, HTTPException
from app.services import citizens_graph_service, residents_graph_service

router = APIRouter()

@router.get("/persons/{spm_person_no}/tree")
def get_unified_tree(spm_person_no: str):
    """Get tree for any person (citizen or resident)"""
    # Try citizens first
    try:
        data = citizens_graph_service.get_person_tree(spm_person_no)
        if data.get("nodes"):
            return data
    except:
        pass
    
    # Try residents
    try:
        data = residents_graph_service.get_person_tree(spm_person_no)
        if data.get("nodes"):
            return data
    except:
        pass
    
    raise HTTPException(status_code=404, detail="Person not found")
