"""FastAPI entrypoint for the SP2 teacher builder."""

from fastapi import FastAPI

from .routes.ingest import router as ingest_router


app = FastAPI(title="SP2 Teacher Builder API")
app.include_router(ingest_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
