"""
Sample target application for demoing Semora against.

This is a deliberately small FastAPI app representing a typical "vibe coded"
project — just enough surface area (a couple of routes, a user model) for
Semora's Spec, Execution, and Threat agents to have something real to analyze.
Do not add production logic here; this repo exists only as a demo fixture.
"""

from fastapi import FastAPI

from auth import router as auth_router

app = FastAPI(title="Sample Target App")
app.include_router(auth_router, prefix="/auth")


@app.get("/")
def root() -> dict:
    """Basic health check route."""
    return {"status": "ok", "app": "sample_target_repo"}
