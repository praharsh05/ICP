from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.graph_service import get_person_tree

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
    Includes biological, step, and guardian relationships.
    
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
                    "source": "step_child_id",
                    "target": "step_parent_id",
                    "type": "STEP_CHILD_OF"
                },
                {
                    "source": "ward_id",
                    "target": "guardian_id",
                    "type": "GUARDIAN_OF"
                },
                {
                    "source": "spouse1_id",
                    "target": "spouse2_id",
                    "type": "SPOUSE_OF"
                },
                ...
            ]
        }
    
    Relationship Types:
        - CHILD_OF: Biological parent-child relationship (child -> parent)
        - STEP_CHILD_OF: Step-parent relationship (step-child -> step-parent)
        - GUARDIAN_OF: Guardian relationship (ward -> guardian)
        - SPOUSE_OF: Marriage relationship (bidirectional)
    
    Kinship Types:
        Biological: self, father, mother, parent, son, daughter, child, 
                   brother, sister, sibling, grandfather, grandmother,
                   grandson, granddaughter, grandchild
        Step: step-father, step-mother, step-parent, step-son, step-daughter,
              step-child, step-brother, step-sister, step-sibling,
              step-grandfather, step-grandmother, step-grandparent
        Guardian: guardian, ward
        Marriage: husband, wife, spouse
    
    Note:
        - Citizens have IDs starting with 'P' (e.g., P0020375801)
        - Residents have IDs starting with 'R' (e.g., R5403276)
        - date_of_birth is only available for residents
        - Step-siblings are biological children of step-parents
        - All relationship types are included in the response for complete family view
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