"""FastAPI entrypoint for the SP2 teacher builder."""

from fastapi import FastAPI

app = FastAPI(title="SP2 Teacher Builder API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
