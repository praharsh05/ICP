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
