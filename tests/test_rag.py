"""Tests for Green Alpha RAG Service."""
import pytest
from unittest.mock import MagicMock, patch


def test_index_stats_empty():
    """Index stats return empty when no vectorstore exists."""
    with patch("app.services.rag_service.FAISS"), \
         patch("app.services.rag_service.OpenAIEmbeddings"), \
         patch("app.services.rag_service.ChatOpenAI"), \
         patch("app.services.rag_service.ChatAnthropic"):
        from app.services.rag_service import RAGService
        svc = RAGService.__new__(RAGService)
        svc.vectorstore = None
        stats = svc.get_index_stats()
        assert stats["status"] == "empty"
        assert stats["total_vectors"] == 0


def test_query_no_documents():
    """Query returns appropriate message when no documents are indexed."""
    with patch("app.services.rag_service.OpenAIEmbeddings"), \
         patch("app.services.rag_service.ChatOpenAI"), \
         patch("app.services.rag_service.ChatAnthropic"):
        from app.services.rag_service import RAGService
        svc = RAGService.__new__(RAGService)
        svc.vectorstore = None
        result = svc.query("What is the carbon footprint?")
        assert "No documents" in result["answer"]
        assert result["sources"] == []


@pytest.mark.asyncio
async def test_api_health(async_client):
    response = await async_client.get("/api/v1/esg/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
