"""FastAPI entrypoint for the SP2 student backend."""

from fastapi import FastAPI

from .api.packs import router as packs_router
from .api.retrieval import router as retrieval_router


app = FastAPI(title="SP2 Student Backend API")
app.include_router(packs_router)
app.include_router(retrieval_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
