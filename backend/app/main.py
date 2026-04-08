from fastapi import FastAPI
from app.db.neo4j_client import neo4j_client
from app.routers.family import router as family_router
from app.routers import auth, users, user_management
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")
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


@app.get("/health")
def health():
    return {"ok": True}

@app.on_event("startup")
def startup_event():
    neo4j_client.connect()
    print("✓ In-memory user store loaded (3 test users: admin, analyst, viewer)")

@app.on_event("shutdown")
def shutdown_event():
    neo4j_client.close()

app.include_router(family_router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(user_management.router)
