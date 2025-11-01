import os
from fastapi import FastAPI
from app.db.neo4j_client import neo4j_client
from app.routers.family import router as family_router
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")  # if you run uvicorn from repo root
# or load_dotenv() if you run uvicorn from backend/ folder
# app/main.py
from fastapi.staticfiles import StaticFiles



app = FastAPI(title="Family Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# quick health route to prove it loads

@app.get("/health")
def health():
    return {"ok": True}

@app.on_event("startup")
def startup_event():
    neo4j_client.connect()

@app.on_event("shutdown")
def shutdown_event():
    neo4j_client.close()

app.include_router(family_router)