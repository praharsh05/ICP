from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.graph_service import get_person_tree
from app.db.neo4j_client import neo4j_client

router = APIRouter(prefix="/api/v1", tags=["family"])

@router.get("/persons/{spm_person_no}/exists")
def check_person_exists(spm_person_no: str):
    """
    Check if a person with the given Unified ID exists in the database.
    
    Args:
        spm_person_no: Unified person number (SPM_PERSON_NO)
        
    Returns:
        {
            "exists": bool,
            "person_type": "citizen" | "resident" | null
        }
    """
    cypher = """
    MATCH (p)
    WHERE (p:Citizen OR p:Resident) AND p.spm_person_no = $id
    RETURN p, labels(p) AS labels
    LIMIT 1
    """
    
    rows = neo4j_client.run(cypher, {"id": spm_person_no})
    
    if not rows or not rows[0]:
        return {"exists": False, "person_type": None}
    
    labels = rows[0].get("labels", [])
    person_type = None
    if "Citizen" in labels:
        person_type = "citizen"
    elif "Resident" in labels:
        person_type = "resident"
    
    return {"exists": True, "person_type": person_type}

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
                    "name_eng": "Ali Hassan Al Mazrouei",      // English name
                    "name_arabic": "علي حسن المزروعي",         // Arabic name
                    "dob": "2004-09-19",                       // Date of birth
                    "date_of_birth": "2004-09-19",            // Alias for dob
                    "unified_id": "P0020375801",               // Unified person ID
                    "passport_no": "PA22710627",               // Passport number
                    "passport": "PA22710627",                  // Alias for passport_no
                    "contact_no": "+971501234567",             // Contact number
                    "nationality": "UAE",                      // Nationality
                    "gender": "M",                              // Gender (M/F)
                    "sex": "M",                                // Alias for gender
                    "national_id": "NID5448510872",            // National ID (may be null)
                    "person_type": "citizen",                  // "citizen" or "resident"
                    "kin": "self"                              // relationship to root person
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
                    "source": "sibling1_id",
                    "target": "sibling2_id",
                    "type": "SIBLING_OF"
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
        - SIBLING_OF: Biological sibling relationship (bidirectional, siblings share at least one parent)
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