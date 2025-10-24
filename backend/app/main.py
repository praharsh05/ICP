import os
from fastapi import FastAPI
from app.db.neo4j_client import neo4j_client
from app.routers.family import router as family_router
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")  # if you run uvicorn from repo root
# or load_dotenv() if you run uvicorn from backend/ folder


app = FastAPI(title="Family Graph API")

# quick health route to prove it loads

# @app.get("/health")
# def health():
#     return {"ok": True}

@app.on_event("startup")
def startup_event():
    neo4j_client.connect()

@app.on_event("shutdown")
def shutdown_event():
    neo4j_client.close()

app.include_router(family_router)