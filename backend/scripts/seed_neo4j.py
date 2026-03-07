"""
Seed Neo4j with mock family data for development/testing.

Family structure (all Citizens with E-prefix IDs):

Generation 1 (Grandparents):
  E1 - Hassan Al Mazrouei (M)   married to   E2 - Fatima Al Mazrouei (F)
  E3 - Khalid Al Rashidi (M)    married to   E4 - Maryam Al Rashidi (F)

Generation 2 (Parents):
  E5 - Omar Al Mazrouei (M)     child of E1+E2,  married to  E6 - Sara Al Rashidi (F, child of E3+E4)
  E7 - Layla Al Mazrouei (F)    child of E1+E2
  E8 - Saif Al Rashidi (M)      child of E3+E4

Generation 3 (Children):
  E9  - Ahmed Al Mazrouei (M)   child of E5+E6
  E10 - Noor Al Mazrouei (F)    child of E5+E6
  E11 - Zayed Al Mazrouei (M)   child of E5+E6

Step/Guardian:
  E12 - Tariq Al Mansoori (M)   step-child of E5 (STEP_CHILD_OF E5)
  E13 - Reem Al Nuaimi (F)      ward of E7 (GUARDIAN_OF E7)

Residents (R-prefix):
  R1 - John Smith (M)           resident, married to E7
  R2 - Priya Patel (F)          resident
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

CITIZENS = [
    # Generation 1
    {
        "spm_person_no": "E1",
        "full_name": "Hassan Al Mazrouei",
        "name_eng": "Hassan Al Mazrouei",
        "name_arabic": "حسن المزروعي",
        "sex": "M",
        "spm_dob": "1950-03-15",
        "nationality": "UAE",
        "passport": "PA10000001",
        "contact_no": "+97150100001",
        "national_id": "NID1000000001",
    },
    {
        "spm_person_no": "E2",
        "full_name": "Fatima Al Mazrouei",
        "name_eng": "Fatima Al Mazrouei",
        "name_arabic": "فاطمة المزروعي",
        "sex": "F",
        "spm_dob": "1955-07-22",
        "nationality": "UAE",
        "passport": "PA10000002",
        "contact_no": "+97150100002",
        "national_id": "NID1000000002",
    },
    {
        "spm_person_no": "E3",
        "full_name": "Khalid Al Rashidi",
        "name_eng": "Khalid Al Rashidi",
        "name_arabic": "خالد الراشدي",
        "sex": "M",
        "spm_dob": "1948-11-05",
        "nationality": "UAE",
        "passport": "PA10000003",
        "contact_no": "+97150100003",
        "national_id": "NID1000000003",
    },
    {
        "spm_person_no": "E4",
        "full_name": "Maryam Al Rashidi",
        "name_eng": "Maryam Al Rashidi",
        "name_arabic": "مريم الراشدي",
        "sex": "F",
        "spm_dob": "1952-02-18",
        "nationality": "UAE",
        "passport": "PA10000004",
        "contact_no": "+97150100004",
        "national_id": "NID1000000004",
    },
    # Generation 2
    {
        "spm_person_no": "E5",
        "full_name": "Omar Al Mazrouei",
        "name_eng": "Omar Al Mazrouei",
        "name_arabic": "عمر المزروعي",
        "sex": "M",
        "spm_dob": "1978-06-10",
        "nationality": "UAE",
        "passport": "PA10000005",
        "contact_no": "+97150100005",
        "national_id": "NID1000000005",
    },
    {
        "spm_person_no": "E6",
        "full_name": "Sara Al Rashidi",
        "name_eng": "Sara Al Rashidi",
        "name_arabic": "سارة الراشدي",
        "sex": "F",
        "spm_dob": "1982-09-25",
        "nationality": "UAE",
        "passport": "PA10000006",
        "contact_no": "+97150100006",
        "national_id": "NID1000000006",
    },
    {
        "spm_person_no": "E7",
        "full_name": "Layla Al Mazrouei",
        "name_eng": "Layla Al Mazrouei",
        "name_arabic": "ليلى المزروعي",
        "sex": "F",
        "spm_dob": "1980-04-14",
        "nationality": "UAE",
        "passport": "PA10000007",
        "contact_no": "+97150100007",
        "national_id": "NID1000000007",
    },
    {
        "spm_person_no": "E8",
        "full_name": "Saif Al Rashidi",
        "name_eng": "Saif Al Rashidi",
        "name_arabic": "سيف الراشدي",
        "sex": "M",
        "spm_dob": "1976-12-30",
        "nationality": "UAE",
        "passport": "PA10000008",
        "contact_no": "+97150100008",
        "national_id": "NID1000000008",
    },
    # Generation 3
    {
        "spm_person_no": "E9",
        "full_name": "Ahmed Al Mazrouei",
        "name_eng": "Ahmed Al Mazrouei",
        "name_arabic": "أحمد المزروعي",
        "sex": "M",
        "spm_dob": "2005-01-20",
        "nationality": "UAE",
        "passport": "PA10000009",
        "contact_no": "+97150100009",
        "national_id": "NID1000000009",
    },
    {
        "spm_person_no": "E10",
        "full_name": "Noor Al Mazrouei",
        "name_eng": "Noor Al Mazrouei",
        "name_arabic": "نور المزروعي",
        "sex": "F",
        "spm_dob": "2007-08-05",
        "nationality": "UAE",
        "passport": "PA10000010",
        "contact_no": "+97150100010",
        "national_id": "NID1000000010",
    },
    {
        "spm_person_no": "E11",
        "full_name": "Zayed Al Mazrouei",
        "name_eng": "Zayed Al Mazrouei",
        "name_arabic": "زايد المزروعي",
        "sex": "M",
        "spm_dob": "2010-03-17",
        "nationality": "UAE",
        "passport": "PA10000011",
        "contact_no": "+97150100011",
        "national_id": "NID1000000011",
    },
    # Step / Guardian
    {
        "spm_person_no": "E12",
        "full_name": "Tariq Al Mansoori",
        "name_eng": "Tariq Al Mansoori",
        "name_arabic": "طارق المنصوري",
        "sex": "M",
        "spm_dob": "2003-11-11",
        "nationality": "UAE",
        "passport": "PA10000012",
        "contact_no": "+97150100012",
        "national_id": "NID1000000012",
    },
    {
        "spm_person_no": "E13",
        "full_name": "Reem Al Nuaimi",
        "name_eng": "Reem Al Nuaimi",
        "name_arabic": "ريم النعيمي",
        "sex": "F",
        "spm_dob": "2015-05-09",
        "nationality": "UAE",
        "passport": "PA10000013",
        "contact_no": "+97150100013",
        "national_id": "NID1000000013",
    },
]

RESIDENTS = [
    {
        "spm_person_no": "R1",
        "full_name": "John Smith",
        "name_eng": "John Smith",
        "name_arabic": "جون سميث",
        "sex": "M",
        "spm_dob": "1979-07-04",
        "nationality": "UK",
        "passport": "GB12345678",
        "contact_no": "+97155100001",
        "national_id": None,
    },
    {
        "spm_person_no": "R2",
        "full_name": "Priya Patel",
        "name_eng": "Priya Patel",
        "name_arabic": "بريا باتيل",
        "sex": "F",
        "spm_dob": "1985-02-28",
        "nationality": "India",
        "passport": "IN87654321",
        "contact_no": "+97155100002",
        "national_id": None,
    },
]

# (child_id, parent_id)
CHILD_OF = [
    ("E5", "E1"), ("E5", "E2"),   # Omar's parents
    ("E6", "E3"), ("E6", "E4"),   # Sara's parents
    ("E7", "E1"), ("E7", "E2"),   # Layla's parents
    ("E8", "E3"), ("E8", "E4"),   # Saif's parents
    ("E9", "E5"), ("E9", "E6"),   # Ahmed's parents
    ("E10", "E5"), ("E10", "E6"), # Noor's parents
    ("E11", "E5"), ("E11", "E6"), # Zayed's parents
]

# (person1_id, person2_id)
SPOUSE_OF = [
    ("E1", "E2"),  # Hassan & Fatima
    ("E3", "E4"),  # Khalid & Maryam
    ("E5", "E6"),  # Omar & Sara
    ("E7", "R1"),  # Layla & John
]

# (step_child_id, step_parent_id)
STEP_CHILD_OF = [
    ("E12", "E5"),  # Tariq is step-child of Omar
]

# (ward_id, guardian_id)
GUARDIAN_OF = [
    ("E13", "E7"),  # Reem is ward of Layla
]


def seed(driver):
    with driver.session(database=NEO4J_DB) as s:
        # Clear existing test data
        s.run("MATCH (n) WHERE n.spm_person_no STARTS WITH 'E' OR n.spm_person_no STARTS WITH 'R' DETACH DELETE n")
        print("Cleared existing seed nodes.")

        # Create Citizens
        for p in CITIZENS:
            s.run(
                """
                CREATE (n:Citizen {
                    spm_person_no: $spm_person_no,
                    full_name: $full_name,
                    name_eng: $name_eng,
                    name_arabic: $name_arabic,
                    sex: $sex,
                    spm_dob: date($spm_dob),
                    nationality: $nationality,
                    passport: $passport,
                    contact_no: $contact_no,
                    national_id: $national_id
                })
                """,
                **p,
            )
        print(f"Created {len(CITIZENS)} citizens.")

        # Create Residents
        for p in RESIDENTS:
            s.run(
                """
                CREATE (n:Resident {
                    spm_person_no: $spm_person_no,
                    full_name: $full_name,
                    name_eng: $name_eng,
                    name_arabic: $name_arabic,
                    sex: $sex,
                    spm_dob: date($spm_dob),
                    nationality: $nationality,
                    passport: $passport,
                    contact_no: $contact_no,
                    national_id: $national_id
                })
                """,
                **p,
            )
        print(f"Created {len(RESIDENTS)} residents.")

        # CHILD_OF
        for child_id, parent_id in CHILD_OF:
            s.run(
                """
                MATCH (child) WHERE child.spm_person_no = $child_id
                MATCH (parent) WHERE parent.spm_person_no = $parent_id
                CREATE (child)-[:CHILD_OF]->(parent)
                """,
                child_id=child_id,
                parent_id=parent_id,
            )
        print(f"Created {len(CHILD_OF)} CHILD_OF edges.")

        # SPOUSE_OF
        for p1, p2 in SPOUSE_OF:
            s.run(
                """
                MATCH (a) WHERE a.spm_person_no = $p1
                MATCH (b) WHERE b.spm_person_no = $p2
                CREATE (a)-[:SPOUSE_OF {status: 'active'}]->(b)
                CREATE (b)-[:SPOUSE_OF {status: 'active'}]->(a)
                """,
                p1=p1,
                p2=p2,
            )
        print(f"Created {len(SPOUSE_OF)} SPOUSE_OF pairs.")

        # STEP_CHILD_OF
        for step_child, step_parent in STEP_CHILD_OF:
            s.run(
                """
                MATCH (sc) WHERE sc.spm_person_no = $step_child
                MATCH (sp) WHERE sp.spm_person_no = $step_parent
                CREATE (sc)-[:STEP_CHILD_OF]->(sp)
                """,
                step_child=step_child,
                step_parent=step_parent,
            )
        print(f"Created {len(STEP_CHILD_OF)} STEP_CHILD_OF edges.")

        # GUARDIAN_OF
        for ward, guardian in GUARDIAN_OF:
            s.run(
                """
                MATCH (w) WHERE w.spm_person_no = $ward
                MATCH (g) WHERE g.spm_person_no = $guardian
                CREATE (w)-[:GUARDIAN_OF]->(g)
                """,
                ward=ward,
                guardian=guardian,
            )
        print(f"Created {len(GUARDIAN_OF)} GUARDIAN_OF edges.")

        print("\nSeed complete. Try these IDs:")
        print("  E1  - Hassan (grandfather, full tree)")
        print("  E5  - Omar   (parent, children + parents + siblings)")
        print("  E9  - Ahmed  (grandchild)")
        print("  E7  - Layla  (has resident spouse R1 and ward E13)")
        print("  R1  - John Smith (resident)")


if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        seed(driver)
    finally:
        driver.close()
