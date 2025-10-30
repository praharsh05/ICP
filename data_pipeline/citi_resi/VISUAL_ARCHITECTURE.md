# Family Tree System - Visual Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SOURCE SYSTEMS                                   │
│  ┌──────────────┐              ┌──────────────┐                         │
│  │   UDB Core   │              │  ECHANNELS   │                         │
│  │  (Citizens)  │              │ (Residents)  │                         │
│  └──────┬───────┘              └──────┬───────┘                         │
└─────────┼──────────────────────────────┼──────────────────────────────┘
          │ CDC                           │ CDC
          ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     BRONZE LAYER (Iceberg/Parquet)                       │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐      │
│  │  Citizens Tables         │    │  Residents Tables            │      │
│  │  • person_master         │    │  • echannels_residency_req  │      │
│  │  • citi_record_master    │    │  • resi_trans                │      │
│  │  • citi_record_detail    │    │  • resi_master               │      │
│  └────────────┬─────────────┘    └────────────┬─────────────────┘      │
└───────────────┼──────────────────────────────┼─────────────────────────┘
                │                               │
                │ Spark: Deduplication          │ Spark: Deduplication
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     SILVER LAYER (Deduplicated)                          │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐      │
│  │  Citizens                │    │  Residents                   │      │
│  │  • person_entity         │    │  • person_entity             │      │
│  │  • person_alias          │    │  • person_alias              │      │
│  │  • parent_links          │    │  • sponsorship_links         │      │
│  │  • spouse_links          │    │  • family_groups             │      │
│  │  • family_membership     │    │                              │      │
│  └────────────┬─────────────┘    └────────────┬─────────────────┘      │
└───────────────┼──────────────────────────────┼─────────────────────────┘
                │                               │
                │ Spark: Ego Network            │ Spark: Ego Network
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  GOLD LAYER (Pre-computed Networks)                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐      │
│  │  citizens_ego3_cache     │    │  residents_ego3_cache        │      │
│  │  • 3-hop family trees    │    │  • 2-hop sponsorship nets    │      │
│  │  • Kinship terms         │    │  • Sponsor relationships     │      │
│  │  • < 2s query time       │    │  • < 2s query time           │      │
│  └────────────┬─────────────┘    └────────────┬─────────────────┘      │
└───────────────┼──────────────────────────────┼─────────────────────────┘
                │                               │
                │ Batch Load                    │ Batch Load
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       NEO4J GRAPH DATABASES                              │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐      │
│  │  Citizens Graph          │    │  Residents Graph             │      │
│  │  database: "citizens"    │    │  database: "residents"       │      │
│  │                          │    │                              │      │
│  │  (:Citizen:Person)       │    │  (:Resident:Person)          │      │
│  │  -[:CHILD_OF]->          │    │  -[:SPONSORED_BY]->          │      │
│  │  -[:SPOUSE_OF]->         │    │                              │      │
│  └────────────┬─────────────┘    └────────────┬─────────────────┘      │
└───────────────┼──────────────────────────────┼─────────────────────────┘
                │                               │
                │ Cypher Query                  │ Cypher Query
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                  │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                    API Routes                                │       │
│  │  /api/v1/citizens/*        /api/v1/residents/*              │       │
│  │      ↓                            ↓                          │       │
│  │  citizens_graph_service    residents_graph_service          │       │
│  │      ↓                            ↓                          │       │
│  │  citizens_neo4j            residents_neo4j                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
└────────────────────────────┬───────────────────────────────────────────┘
                             │ REST API (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       NEXT.JS FRONTEND                                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                   UI Components                              │       │
│  │  ┌──────────────┐              ┌──────────────┐            │       │
│  │  │  Left Panel  │              │ Sigma.js     │            │       │
│  │  │  • Search    │              │ Graph        │            │       │
│  │  │  • Accordion │              │ Visualization│            │       │
│  │  │  • Cards     │              │              │            │       │
│  │  └──────────────┘              └──────────────┘            │       │
│  └─────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow for Citizen Query

```
1. User enters spm_person_no: "P1968702237"
                 ↓
2. Frontend → API: GET /api/v1/citizens/persons/P1968702237/tree?depth=3
                 ↓
3. Backend → Neo4j Citizens DB: MATCH (p:Citizen {spm_person_no: "P1968702237"})
                 ↓
4. Neo4j traverses: ego -[:CHILD_OF]-> parents -[:CHILD_OF]-> grandparents
                    ego <-[:CHILD_OF]- children <-[:CHILD_OF]- grandchildren
                    ego -[:SPOUSE_OF]- spouses
                    ego -[:CHILD_OF]-> parent <-[:CHILD_OF]- siblings
                 ↓
5. Backend computes kinship terms & clusters
                 ↓
6. Backend → Frontend: JSON with nodes & edges
                 ↓
7. Sigma.js renders graph:
   • Gold nodes for citizens
   • Solid lines for CHILD_OF
   • Dashed lines for SPOUSE_OF
                 ↓
8. User sees interactive family tree < 2 seconds!
```

## Data Flow for Resident Query

```
1. User enters spm_person_no: "R9876543"
                 ↓
2. Frontend → API: GET /api/v1/residents/persons/R9876543/tree?depth=2
                 ↓
3. Backend → Neo4j Residents DB: MATCH (p:Resident {spm_person_no: "R9876543"})
                 ↓
4. Neo4j traverses: ego -[:SPONSORED_BY*1..2]-> sponsors
                    ego <-[:SPONSORED_BY*1..2]- sponsored_persons
                 ↓
5. Backend enriches with relation_to_sponsor labels
                 ↓
6. Backend → Frontend: JSON with nodes & edges
                 ↓
7. Sigma.js renders graph:
   • Blue nodes for residents
   • Gold/Blue nodes if sponsor is citizen (cross-boundary)
   • Dotted lines for SPONSORED_BY
                 ↓
8. User sees sponsorship network < 2 seconds!
```

## Entity Resolution Flow

### Citizens Deduplication
```
person_master (raw data with duplicates)
     ↓
1. Normalize fields:
   • name_norm = lower(trim(spm_full_aname))
   • dob_norm = to_date(spm_dob)
   • national_id_norm = remove_spaces(spm_national_id)
     ↓
2. Clustering rules (priority order):
   ┌─────────────────────────────────────────┐
   │ Rule 1: national_id_norm + dob_norm    │ → Confidence: 1.0
   ├─────────────────────────────────────────┤
   │ Rule 2: name_norm + dob_norm + gender  │ → Confidence: 0.9
   ├─────────────────────────────────────────┤
   │ Rule 3: spm_person_no (anchor)         │ → Confidence: 0.8
   └─────────────────────────────────────────┘
     ↓
3. Generate entity_person_id = "C:" + SHA256(cluster_key)
     ↓
4. Select best record per entity:
   • Highest completeness score
   • Most recent updated_at
     ↓
5. Output tables:
   • citizens_person_entity (golden records)
   • citizens_person_alias (all spm_person_no → entity_person_id mappings)
```

### Residents Deduplication
```
echannels_residency_requests (multiple records per person)
     ↓
1. Normalize fields:
   • passport_norm = upper(remove_spaces(passport_number))
   • dob_norm = to_date(date_of_birth)
   • name_norm = lower(trim(english_full_name))
     ↓
2. Clustering rules (priority order):
   ┌─────────────────────────────────────────┐
   │ Rule 1: spm_person_no (if available)   │ → Confidence: 1.0
   ├─────────────────────────────────────────┤
   │ Rule 2: passport_norm + dob_norm       │ → Confidence: 0.95
   ├─────────────────────────────────────────┤
   │ Rule 3: name_norm + dob_norm + nat     │ → Confidence: 0.85
   ├─────────────────────────────────────────┤
   │ Rule 4: request_id + sponsor_number    │ → Confidence: 0.7
   └─────────────────────────────────────────┘
     ↓
3. Generate entity_person_id = "R:" + SHA256(cluster_key)
     ↓
4. Select most complete and recent record
     ↓
5. Output tables:
   • residents_person_entity
   • residents_person_alias
```

## Link Building Flow

### Citizens Family Links
```
citi_record_detail
     ↓
1. Join with person_alias to get entity IDs:
   child.spm_person_no → child_entity_id
   father.spm_person_no_father → father_entity_id
   mother.spm_person_no_mother → mother_entity_id
     ↓
2. Create parent_links:
   (child_entity_id) -[:CHILD_OF]-> (father_entity_id)
   (child_entity_id) -[:CHILD_OF]-> (mother_entity_id)
     ↓
3. Detect spouses:
   rel1_code = 2 (wife) → Join with family head
   (head_entity_id) -[:SPOUSE_OF]-> (wife_entity_id)
     ↓
4. Track family membership:
   person → crm_seq (family book)
     ↓
Output: parent_links, spouse_links, family_membership tables
```

### Residents Sponsorship Links
```
residents_person_entity (with sponsor_number)
     ↓
1. Lookup sponsor_number in both:
   • citizens_person_alias
   • residents_person_alias
     ↓
2. Create sponsorship_links:
   (sponsored_entity_id) -[:SPONSORED_BY]-> (sponsor_entity_id)
   Include: relation_to_sponsor, sponsor_type
     ↓
3. Group by sponsor:
   family_group_id = "SPON:" + sponsor_number
     ↓
Output: sponsorship_links, family_groups tables
```

## Ego Network Computation

### Citizens (3-hop BFS)
```
Start: entity_person_id = "C:abc123"
     ↓
BFS Traversal:
┌──────────────────────────────────────┐
│ Hop 0: ego                           │
├──────────────────────────────────────┤
│ Hop 1: parents, children, spouses   │
├──────────────────────────────────────┤
│ Hop 2: grandparents, grandchildren, │
│        siblings, in-laws             │
├──────────────────────────────────────┤
│ Hop 3: great-grandparents, uncles,  │
│        nephews, cousins              │
└──────────────────────────────────────┘
     ↓
For each node, compute:
• Kinship term (father, mother, brother, cousin, etc.)
• Cluster (ancestors, descendants, spouses, inlaws)
     ↓
Output: ego_json = {
  root: "C:abc123",
  nodes: [{id, label, sex, kin, cluster}],
  edges: [{source, target, type}]
}
```

### Residents (2-hop BFS)
```
Start: entity_person_id = "R:xyz789"
     ↓
BFS Traversal:
┌──────────────────────────────────────┐
│ Hop 0: ego                           │
├──────────────────────────────────────┤
│ Hop 1: sponsor, sponsored persons    │
├──────────────────────────────────────┤
│ Hop 2: sponsor's sponsor,            │
│        sponsored's sponsored         │
└──────────────────────────────────────┘
     ↓
For each node:
• Label with relation_to_sponsor
• Mark sponsor_type (citizen/resident)
     ↓
Output: ego_json = {
  root: "R:xyz789",
  nodes: [{id, label, person_type}],
  edges: [{source, target, type: "SPONSORED_BY"}]
}
```

## Neo4j Graph Structure

### Citizens Graph Schema
```cypher
// Nodes
(:Citizen:Person {
  entity_person_id: "C:abc123",
  spm_person_no: "P1234567",
  full_name: "Ahmed Mohammed Al Balushi",
  full_name_ar: "أحمد محمد البلوشي",
  full_name_en: "Ahmed Mohammed Al Balushi",
  sex: "M",
  dob: "1985-03-15",
  nationality_code: 232,
  person_type: "citizen"
})

// Relationships
(:Citizen)-[:CHILD_OF {parent_type: "father", confidence: 1.0}]->(:Citizen)
(:Citizen)-[:SPOUSE_OF {confidence: 0.9}]->(:Citizen)
(:Citizen)-[:MEMBER_OF {family_book_id: "FAM:12345"}]->(:FamilyBook)

// Indexes
CREATE INDEX FOR (p:Person) ON (p.entity_person_id)
CREATE INDEX FOR (p:Person) ON (p.spm_person_no)
CREATE INDEX FOR (c:Citizen) ON (c.entity_person_id)
```

### Residents Graph Schema
```cypher
// Nodes
(:Resident:Person {
  entity_person_id: "R:xyz789",
  spm_person_no: "R9876543",
  full_name: "John Smith",
  sex: "M",
  dob: "1990-07-20",
  nationality_code: 826,
  sponsor_number: "P5237",
  person_type: "resident"
})

// Cross-boundary sponsor node (citizen)
(:Person {
  entity_person_id: "C:abc123",
  person_type: "citizen"
})

// Relationships
(:Resident)-[:SPONSORED_BY {
  relation_to_sponsor: "Son",
  confidence: 1.0
}]->(:Person)

(:Resident)-[:MEMBER_OF {
  family_group_id: "SPON:5237"
}]->(:SponsorGroup)

// Indexes
CREATE INDEX FOR (p:Person) ON (p.entity_person_id)
CREATE INDEX FOR (p:Person) ON (p.spm_person_no)
CREATE INDEX FOR (r:Resident) ON (r.entity_person_id)
CREATE INDEX FOR (r:Resident) ON (r.sponsor_number)
```

## API Response Examples

### Citizen Tree Response
```json
{
  "root": "P1968702237",
  "person_type": "citizen",
  "nodes": [
    {
      "id": "P1968702237",
      "entity_id": "C:a3f2c9...",
      "label": "Fatima bint Ahmed",
      "label_ar": "فاطمة بنت أحمد",
      "sex": "F",
      "dob": "1995-05-15",
      "kin": "self",
      "cluster": "self",
      "person_type": "citizen"
    },
    {
      "id": "P1234567",
      "entity_id": "C:7e9b14...",
      "label": "Ahmed Mohammed Al Balushi",
      "sex": "M",
      "kin": "father",
      "cluster": "ancestors",
      "person_type": "citizen"
    },
    {
      "id": "P2345678",
      "entity_id": "C:1c8d3a...",
      "label": "Aisha bint Hamad",
      "sex": "F",
      "kin": "mother",
      "cluster": "ancestors",
      "person_type": "citizen"
    },
    {
      "id": "P3456789",
      "entity_id": "C:9f2e1b...",
      "label": "Salem bin Khalid",
      "sex": "M",
      "kin": "husband",
      "cluster": "spouses",
      "person_type": "citizen"
    }
  ],
  "edges": [
    {"source": "P1968702237", "target": "P1234567", "type": "CHILD_OF"},
    {"source": "P1968702237", "target": "P2345678", "type": "CHILD_OF"},
    {"source": "P1968702237", "target": "P3456789", "type": "SPOUSE_OF"},
    {"source": "P3456789", "target": "P1968702237", "type": "SPOUSE_OF"}
  ]
}
```

### Resident Tree Response
```json
{
  "root": "R9876543",
  "person_type": "resident",
  "nodes": [
    {
      "id": "R9876543",
      "entity_id": "R:7e9b14...",
      "label": "John Smith",
      "sex": "M",
      "dob": "1990-07-20",
      "person_type": "resident",
      "sponsor_number": "P5237"
    },
    {
      "id": "P5237",
      "entity_id": "C:a3f2c9...",
      "label": "Mohammed Al Nahyan",
      "sex": "M",
      "person_type": "citizen"
    },
    {
      "id": "R8765432",
      "entity_id": "R:3c1a8f...",
      "label": "Jane Smith",
      "sex": "F",
      "person_type": "resident",
      "sponsor_number": "P5237"
    }
  ],
  "edges": [
    {
      "source": "R9876543",
      "target": "P5237",
      "type": "SPONSORED_BY",
      "relation": "Employee"
    },
    {
      "source": "R8765432",
      "target": "P5237",
      "type": "SPONSORED_BY",
      "relation": "Employee's Wife"
    }
  ]
}
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │                    Load Balancer                          │          │
│  │                   (Ingress Controller)                    │          │
│  └────────┬─────────────────────────────────────────────────┘          │
│           │                                                              │
│           ├───────────────┬──────────────────┬───────────────┐         │
│           ▼               ▼                  ▼               ▼         │
│  ┌────────────┐  ┌────────────┐   ┌────────────┐  ┌────────────┐     │
│  │ FastAPI    │  │ FastAPI    │   │ FastAPI    │  │ FastAPI    │     │
│  │ Pod 1      │  │ Pod 2      │   │ Pod 3      │  │ Pod 4      │     │
│  └─────┬──────┘  └─────┬──────┘   └─────┬──────┘  └─────┬──────┘     │
│        │                │                 │                │            │
│        └────────────────┴─────────────────┴────────────────┘            │
│                                 │                                        │
│                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │              Neo4j StatefulSet (2 instances)             │          │
│  │  ┌────────────────────┐      ┌────────────────────┐     │          │
│  │  │  Citizens DB       │      │  Residents DB      │     │          │
│  │  │  Port: 7687        │      │  Port: 7688        │     │          │
│  │  │  Memory: 64GB      │      │  Memory: 64GB      │     │          │
│  │  └────────────────────┘      └────────────────────┘     │          │
│  └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         SPARK CLUSTER (YARN)                             │
│  ┌────────────┐  ┌──────────────────────────────────────────┐          │
│  │   Driver   │  │          Executors (50-100)             │          │
│  └────────────┘  └──────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA LAKE (MinIO/S3)                                │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  Iceberg Tables                                        │             │
│  │  • Bronze: ~1TB (raw data)                             │             │
│  │  • Silver: ~500GB (deduplicated)                       │             │
│  │  • Gold: ~2TB (ego caches)                             │             │
│  └────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         AIRFLOW                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                        │
│  │ Webserver  │  │ Scheduler  │  │  Workers   │                        │
│  └────────────┘  └────────────┘  └────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                                │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  Vercel / Nginx                                        │             │
│  │  • CDN: CloudFlare                                     │             │
│  │  • Edge caching                                        │             │
│  └────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

This architecture ensures:
- ✅ High availability (multiple API pods)
- ✅ Horizontal scalability (add more pods/executors)
- ✅ Fast queries (Neo4j in-memory graph)
- ✅ Large dataset support (distributed Spark processing)
- ✅ Low latency (CDN for frontend, pre-computed caches)
