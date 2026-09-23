"""Unified FastAPI entrypoint for the SP2 backend."""

import logging

from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.ingest import router as ingest_router
from backend.routes.packs import router as packs_router
from backend.routes.retrieval import router as retrieval_router
from backend.routes.settings import router as settings_router
from backend.routes.summaries import router as summaries_router
from storage.database.setup.create_sqlite_db import create_sqlite_db


logging.basicConfig(level=logging.WARNING)

# Runs schema creation/migration once at startup, so a request never races
# an on-disk database that predates a newer column (e.g. source_zip_path).
create_sqlite_db()

app = FastAPI(title="SP2 Backend API")
app.include_router(health_router)
app.include_router(packs_router)
app.include_router(retrieval_router)
app.include_router(settings_router)
app.include_router(summaries_router)
app.include_router(ingest_router)
