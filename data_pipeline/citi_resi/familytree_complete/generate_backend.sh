#!/bin/bash

PROJECT_ROOT="/home/claude/familytree_complete"
cd $PROJECT_ROOT

echo "Generating Backend API..."

# Main FastAPI app
cat > backend/main.py << 'EOFPYTHON'
"""
Family Tree API - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import citizens, residents, unified

app = FastAPI(
    title="Family Tree API",
    version="1.0.0",
    description="API for family tree visualization supporting citizens and residents"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(citizens.router, prefix="/api/v1/citizens", tags=["citizens"])
app.include_router(residents.router, prefix="/api/v1/residents", tags=["residents"])
app.include_router(unified.router, prefix="/api/v1/unified", tags=["unified"])

@app.get("/")
def root():
    return {"message": "Family Tree API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
EOFPYTHON

# App __init__.py
cat > backend/app/__init__.py << 'EOFPYTHON'
"""
Family Tree API Application
"""
__version__ = "1.0.0"
EOFPYTHON

# Database clients
mkdir -p backend/app/db
cat > backend/app/db/__init__.py << 'EOFPYTHON'
"""Database clients"""
EOFPYTHON

cat > backend/app/db/neo4j_client.py << 'EOFPYTHON'
"""
Neo4j Client for dual database support
"""
import os
from neo4j import GraphDatabase, Driver
from typing import Optional

class Neo4jClient:
    def __init__(self, database: str = "neo4j"):
        self._driver: Optional[Driver] = None
        self.database = database
    
    def connect(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def run(self, cypher: str, params: dict = None):
        if self._driver is None:
            self.connect()
        with self._driver.session(database=self.database) as session:
            return list(session.run(cypher, params or {}))

# Create clients for both databases
citizens_neo4j = Neo4jClient(database="citizens")
residents_neo4j = Neo4j Client(database="residents")
EOFPYTHON

# API routes
mkdir -p backend/app/api
cat > backend/app/api/__init__.py << 'EOFPYTHON'
"""API routes"""
EOFPYTHON

cat > backend/app/api/citizens.py << 'EOFPYTHON'
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
EOFPYTHON

cat > backend/app/api/residents.py << 'EOFPYTHON'
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
EOFPYTHON

cat > backend/app/api/unified.py << 'EOFPYTHON'
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
EOFPYTHON

# Services
mkdir -p backend/app/services
cat > backend/app/services/__init__.py << 'EOFPYTHON'
"""Graph services"""
EOFPYTHON

cat > backend/app/services/citizens_graph_service.py << 'EOFPYTHON'
"""
Citizens Graph Service
"""
from typing import Dict, Any, List
from app.db.neo4j_client import citizens_neo4j

def get_person_tree(spm_person_no: str, depth: int = 3, lang: str = "en") -> Dict[str, Any]:
    """Get family tree for a citizen"""
    
    cypher = f"""
    MATCH (ego:Citizen {{spm_person_no: $id}})
    
    OPTIONAL MATCH (ego)-[:CHILD_OF*1..{depth-1}]->(anc:Citizen)
    OPTIONAL MATCH (ego)<-[:CHILD_OF*1..{depth-1}]-(desc:Citizen)
    OPTIONAL MATCH (ego)-[:SPOUSE_OF]-(sp:Person)
    OPTIONAL MATCH (ego)-[:CHILD_OF]->(p:Citizen)<-[:CHILD_OF]-(sib:Citizen)
    WHERE sib <> ego
    
    WITH ego, [ego] + collect(DISTINCT anc) + collect(DISTINCT desc) + 
         collect(DISTINCT sp) + collect(DISTINCT sib) AS all_nodes
    UNWIND all_nodes AS n
    WITH ego, collect(DISTINCT n) AS nodes
    
    UNWIND nodes AS c
    OPTIONAL MATCH (c)-[:CHILD_OF]->(p:Person)
    WHERE p IN nodes
    WITH ego, nodes, collect(DISTINCT {{
        source: c.spm_person_no,
        target: p.spm_person_no,
        type: 'CHILD_OF'
    }}) AS child_edges
    
    UNWIND nodes AS a
    OPTIONAL MATCH (a)-[:SPOUSE_OF]-(b:Person)
    WHERE b IN nodes AND a.spm_person_no < b.spm_person_no
    WITH ego, nodes, child_edges, collect(DISTINCT {{
        source: a.spm_person_no,
        target: b.spm_person_no,
        type: 'SPOUSE_OF'
    }}) AS spouse_edges
    
    WITH ego, nodes, (child_edges + spouse_edges) AS edges
    
    UNWIND nodes AS n
    RETURN ego, collect({{
      id: n.spm_person_no,
      entity_id: n.entity_person_id,
      label: coalesce(n.full_name, n.spm_person_no),
      sex: n.sex,
      person_type: n.person_type,
      kin: CASE
        WHEN n = ego THEN 'self'
        WHEN (n)-[:SPOUSE_OF]-(ego) THEN 'spouse'
        WHEN (ego)-[:CHILD_OF]->(n) THEN 'parent'
        WHEN (n)-[:CHILD_OF]->(ego) THEN 'child'
        ELSE 'relative'
      END
    }}) AS nodes, edges
    """
    
    rows = citizens_neo4j.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}
    
    rec = rows[0]
    return {
        "root": spm_person_no,
        "nodes": rec["nodes"] or [],
        "edges": rec["edges"] or [],
        "person_type": "citizen"
    }

def lowest_common_ancestors(p1: str, p2: str, limit: int = 5) -> List[Dict]:
    """Find lowest common ancestors"""
    cypher = """
    MATCH (a:Citizen {spm_person_no:$p1}), (b:Citizen {spm_person_no:$p2})
    MATCH pathA = (a)-[:CHILD_OF*0..10]->(anc:Citizen)
    WITH b, anc, length(pathA) AS da
    MATCH pathB = (b)-[:CHILD_OF*0..10]->(anc)
    RETURN anc.spm_person_no AS ancestor_id,
           anc.full_name AS full_name,
           da, 
           length(pathB) AS db,
           (da + length(pathB)) AS total_depth
    ORDER BY total_depth ASC
    LIMIT $limit
    """
    
    rows = citizens_neo4j.run(cypher, {"p1": p1, "p2": p2, "limit": limit})
    return [dict(r) for r in rows]
EOFPYTHON

cat > backend/app/services/residents_graph_service.py << 'EOFPYTHON'
"""
Residents Graph Service
"""
from typing import Dict, Any
from app.db.neo4j_client import residents_neo4j

def get_person_tree(spm_person_no: str, depth: int = 2) -> Dict[str, Any]:
    """Get sponsorship network for a resident"""
    
    cypher = f"""
    MATCH (ego:Resident {{spm_person_no: $id}})
    
    OPTIONAL MATCH path1 = (ego)-[:SPONSORED_BY*1..{depth}]->(sponsor:Person)
    OPTIONAL MATCH path2 = (ego)<-[:SPONSORED_BY*1..{depth}]-(sponsored:Resident)
    
    WITH ego, [ego] + collect(DISTINCT sponsor) + collect(DISTINCT sponsored) AS all_nodes
    UNWIND all_nodes AS n
    WITH ego, collect(DISTINCT n) AS nodes
    
    UNWIND nodes AS sponsored
    OPTIONAL MATCH (sponsored)-[r:SPONSORED_BY]->(sponsor:Person)
    WHERE sponsor IN nodes
    WITH ego, nodes, collect(DISTINCT {{
        source: sponsored.spm_person_no,
        target: sponsor.spm_person_no,
        type: 'SPONSORED_BY'
    }}) AS edges
    
    UNWIND nodes AS n
    RETURN ego, collect({{
      id: n.spm_person_no,
      entity_id: n.entity_person_id,
      label: coalesce(n.full_name, n.spm_person_no),
      sex: n.sex,
      person_type: n.person_type
    }}) AS nodes, edges
    """
    
    rows = residents_neo4j.run(cypher, {"id": spm_person_no})
    if not rows:
        return {"root": spm_person_no, "nodes": [], "edges": []}
    
    rec = rows[0]
    return {
        "root": spm_person_no,
        "nodes": rec["nodes"] or [],
        "edges": rec["edges"] or [],
        "person_type": "resident"
    }

def get_sponsorship_family(sponsor_id: str) -> Dict[str, Any]:
    """Get all persons sponsored by a sponsor"""
    cypher = """
    MATCH (sponsor:Person {spm_person_no: $id})
    OPTIONAL MATCH (sponsor)<-[:SPONSORED_BY]-(sponsored:Resident)
    RETURN sponsor, collect({{
      id: sponsored.spm_person_no,
      label: coalesce(sponsored.full_name, sponsored.spm_person_no),
      sex: sponsored.sex
    }}) AS sponsored_persons
    """
    
    rows = residents_neo4j.run(cypher, {"id": sponsor_id})
    if not rows:
        return {"sponsor": sponsor_id, "sponsored": []}
    
    rec = rows[0]
    return {
        "sponsor": sponsor_id,
        "sponsored": rec["sponsored_persons"] or []
    }
EOFPYTHON

# Requirements
cat > backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
neo4j==5.14.0
trino==0.327.0
pydantic==2.5.0
python-multipart==0.0.6
EOF

# Docker
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Docker Compose
cat > backend/docker-compose.yml << 'EOF'
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
      - TRINO_HOST=trino
      - TRINO_PORT=8080
    depends_on:
      - neo4j
    networks:
      - familytree

  neo4j:
    image: neo4j:5.13
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_server_memory_heap_max__size=4G
    volumes:
      - neo4j_data:/data
    networks:
      - familytree

networks:
  familytree:
    driver: bridge

volumes:
  neo4j_data:
EOF

echo "✓ Backend API generated"

