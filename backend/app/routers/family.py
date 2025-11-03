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
        GET /api/v1/persons/P0020375801/tree
        GET /api/v1/persons/P0020375801/tree?depth=5
        GET /api/v1/persons/P0020375801/tree?person_type=citizen
        GET /api/v1/persons/R5403276/tree?depth=5&person_type=resident
    
    Response format:
        {
            "root": "P0020375801",
            "nodes": [
                {
                    "id": "P0020375801",
                    "label": "Ali Hassan Al Mazrouei",
                    "full_name": "Ali Hassan Al Mazrouei",
                    "sex": "M",
                    "date_of_birth": "2004-09-19",       // null for citizens, date for residents
                    "national_id": "NID5448510872",      // may be null
                    "passport": "PA22710627",             // may be null
                    "person_type": "citizen",             // "citizen" or "resident"
                    "kin": "self"                         // relationship to root person
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
    
    Note:
        - Citizens have IDs starting with 'P' (e.g., P0020375801)
        - Residents have IDs starting with 'R' (e.g., R5403276)
        - date_of_birth is only available for residents
        - kin types: self, husband, wife, spouse, father, mother, parent, son, daughter, child,
                     brother, sister, sibling, paternal grandfather, paternal grandmother,
                     maternal grandfather, maternal grandmother, grandson, granddaughter, grandchild
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
        GET /api/v1/lca?p1=P0020375801&p2=P0034751727
        GET /api/v1/lca?p1=R5403276&p2=R6873285&limit=10
    
    Response format:
        [
            {
                "ancestor_id": "P0224686427",
                "full_name": "Nasser Hassan Al Mazrouei",
                "da": 2,           // depth from p1 to ancestor
                "db": 3,           // depth from p2 to ancestor
                "total_depth": 5   // combined depth
            },
            ...
        ]
    
    Note:
        - Works across both citizens and residents
        - Returns ancestors ordered by total_depth (shortest path first)
        - If p1 and p2 are the same person, returns that person with depth 0
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