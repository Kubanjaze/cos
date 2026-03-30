"""COS API — FastAPI application entry point.

Run: uvicorn cos.api.main:app --reload --port 8000
Browse: http://localhost:8000
API docs: http://localhost:8000/docs
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from cos.api.routes import core, memory, reasoning, workflow, decision, autonomy

app = FastAPI(
    title="COS — Cognitive Operating System",
    version="1.0.0",
    description="A unified system that ingests information, constructs structured memory, "
                "reasons across it, and produces decisions + executable workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(core.router, prefix="/api", tags=["Core"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(reasoning.router, prefix="/api", tags=["Reasoning"])
app.include_router(workflow.router, prefix="/api", tags=["Workflow"])
app.include_router(decision.router, prefix="/api", tags=["Decision"])
app.include_router(autonomy.router, prefix="/api", tags=["Autonomy"])

# Serve static frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the React SPA."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "COS API running. Visit /docs for API documentation."}
