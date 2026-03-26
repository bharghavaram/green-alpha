"""Green Alpha – ESG query and document management routes."""
import shutil
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.services.rag_service import RAGService, get_rag_service

router = APIRouter(prefix="/esg", tags=["ESG Intelligence"])


class QueryRequest(BaseModel):
    question: str
    use_anthropic: bool = False


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    model: str


@router.post("/query", response_model=QueryResponse)
async def query_esg(request: QueryRequest, service: RAGService = Depends(get_rag_service)):
    """Query the ESG knowledge base using RAG with CoT analysis."""
    result = service.query(request.question, request.use_anthropic)
    return QueryResponse(**result)


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    service: RAGService = Depends(get_rag_service),
):
    """Upload ESG documents (PDF/TXT) to the knowledge base."""
    saved_paths = []
    tmp_dir = tempfile.mkdtemp()
    try:
        for file in files:
            if not file.filename.endswith((".pdf", ".txt")):
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
            dest = Path(tmp_dir) / file.filename
            with open(dest, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_paths.append(str(dest))

        chunks_added = service.add_documents(saved_paths)
        return {
            "message": f"Successfully indexed {len(files)} document(s)",
            "chunks_added": chunks_added,
            "files": [f.filename for f in files],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/stats")
async def get_stats(service: RAGService = Depends(get_rag_service)):
    """Get knowledge base statistics."""
    return service.get_index_stats()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Green Alpha ESG Intelligence Platform"}
