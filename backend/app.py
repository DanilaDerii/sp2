"""FastAPI entrypoint for SP2."""

from fastapi import FastAPI

app = FastAPI(title="SP2 Local API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
