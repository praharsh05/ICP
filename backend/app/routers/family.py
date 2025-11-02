from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.graph_service import get_person_tree, lowest_common_ancestors

router = APIRouter(prefix="/api/v1", tags=["family"])

@router.get("/persons/{spm_person_no}/tree")
def read_tree(
    spm_person_no: str, 
    depth: int = Query(3, ge=1, le=5),
    person_type: Optional[str] = Query(None, regex="^(citizen|resident)$"),
    lang: str = "en"
):
    """
    Get family tree for a person with optional person_type filtering.
    
    Args:
        spm_person_no: Unified person number (SPM_PERSON_NO)
        depth: Tree depth (1-5, default 3)
        person_type: Optional filter for person type ('citizen' or 'resident')
        lang: Language code (default 'en')
        
    Returns:
        Family tree data with nodes and edges
        
    Examples:
        GET /api/v1/persons/123456/tree
        GET /api/v1/persons/123456/tree?depth=5
        GET /api/v1/persons/123456/tree?person_type=citizen
        GET /api/v1/persons/123456/tree?depth=5&person_type=resident
    
    Response format:
        {
            "root": "123456",
            "nodes": [
                {
                    "id": "123456",
                    "label": "Ahmed Mohammed",
                    "full_name": "Ahmed Mohammed Ali",
                    "sex": "M",
                    "date_of_birth": "1985-01-15",
                    "national_id": "784-1985-1234567-1",  // citizens only
                    "passport": "A12345678",                // both
                    "person_type": "citizen",               // citizen or resident
                    "life_status": "alive",
                    "nationality": "AE",
                    "kin": "self"
                },
                ...
            ],
            "edges": [
                {
                    "source": "child_id",
                    "target": "parent_id",
                    "type": "CHILD_OF"
                },
                {
                    "source": "spouse1_id",
                    "target": "spouse2_id",
                    "type": "SPOUSE_OF"
                },
                ...
            ]
        }
    """
    # Get tree data from graph service
    data = get_person_tree(
        spm_person_no, 
        depth=depth,
        person_type=person_type
    )
    
    # Return empty result if no nodes found
    # This allows UI to show "No data found" message
    if not data["nodes"]:
        return data
    
    return data

@router.get("/lca")
def read_lca(
    p1: str, 
    p2: str, 
    limit: int = Query(5, ge=1, le=20)
):
    """
    Find lowest common ancestors (LCA) between two persons.
    
    Args:
        p1: First person's unified number
        p2: Second person's unified number
        limit: Maximum number of ancestors to return (1-20, default 5)
        
    Returns:
        List of common ancestors with depth information
        
    Examples:
        GET /api/v1/lca?p1=123456&p2=789012
        GET /api/v1/lca?p1=123456&p2=789012&limit=10
    
    Response format:
        [
            {
                "ancestor_id": "345678",
                "full_name": "Mohammed Ali Hassan",
                "da": 2,           // depth from p1 to ancestor
                "db": 3,           // depth from p2 to ancestor
                "total_depth": 5   // combined depth
            },
            ...
        ]
    """
    # Handle same person case
    if p1 == p2:
        # Same person is their own ancestor with depth 0
        return [{
            "ancestor_id": p1, 
            "full_name": None, 
            "da": 0, 
            "db": 0, 
            "total_depth": 0
        }]
    
    # Find common ancestors
    res = lowest_common_ancestors(p1, p2, limit=limit)
    return res
