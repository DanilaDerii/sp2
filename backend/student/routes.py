"""Student-side API routes."""

from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.paths import TMP_DIR, ensure_runtime_dirs
from backend.student.chat import answer_question
from backend.student.importer import import_pack_zip
from backend.student.schemas import ChatRequest, ChatResponseBody, RetrievedChunkResponse


router = APIRouter(prefix="/student", tags=["student"])


@router.post("/import-pack")
async def import_pack(file: UploadFile = File(...)) -> dict:
    """Import a teacher-built pack zip into local student storage."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a name")
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip pack")

    ensure_runtime_dirs()
    temp_zip_path = TMP_DIR / file.filename

    try:
        data = await file.read()
        temp_zip_path.write_bytes(data)
        imported_pack = import_pack_zip(temp_zip_path)
        return {"pack": asdict(imported_pack)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        await file.close()


@router.post("/chat", response_model=ChatResponseBody)
async def chat(request: ChatRequest) -> ChatResponseBody:
    """Answer a student question against one imported pack."""
    try:
        response = answer_question(
            request.question,
            request.pack_id,
            top_k=request.top_k,
        )
        return ChatResponseBody(
            pack_id=response.pack_id,
            question=response.question,
            answer=response.answer,
            used_debug_fallback=response.used_debug_fallback,
            retrieved_chunks=[
                RetrievedChunkResponse(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    source_type=chunk.source_type,
                    source_title=chunk.source_title,
                    text=chunk.text,
                    chunk_index=chunk.chunk_index,
                    page=chunk.page,
                    section=chunk.section,
                    topic=chunk.topic,
                    distance=chunk.distance,
                )
                for chunk in response.retrieved_chunks
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
