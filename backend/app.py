"""FastAPI entrypoint for SP2."""

from fastapi import FastAPI

from backend.storage.sqlite import initialize_database
from backend.student.routes import router as student_router

app = FastAPI(title="SP2 Local API")


@app.on_event("startup")
async def startup() -> None:
    initialize_database()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(student_router)
