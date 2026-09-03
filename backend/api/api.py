"""Unified FastAPI entrypoint for the SP2 backend."""

from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.ingest import router as ingest_router
from backend.routes.packs import router as packs_router
from backend.routes.retrieval import router as retrieval_router


app = FastAPI(title="SP2 Backend API")
app.include_router(health_router)
app.include_router(packs_router)
app.include_router(retrieval_router)
app.include_router(ingest_router)
