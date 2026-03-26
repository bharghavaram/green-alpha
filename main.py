"""
Green Alpha – ESG & Sustainability Intelligence Platform
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.routes.esg import router as esg_router

app = FastAPI(
    title="Green Alpha – ESG Intelligence Platform",
    description=(
        "Production-grade RAG system for ESG & Sustainability analysis. "
        "Indexes 100+ ESG documents with FAISS semantic search, CoT reasoning via GPT-4 and Claude, "
        "supporting 20+ concurrent users."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(esg_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "Green Alpha – ESG & Sustainability Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "query": "POST /api/v1/esg/query",
            "upload": "POST /api/v1/esg/upload",
            "stats": "GET /api/v1/esg/stats",
        },
    }


if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
