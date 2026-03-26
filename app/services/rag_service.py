"""
Green Alpha RAG Service – FAISS-based retrieval over ESG documents.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from app.core.config import settings

logger = logging.getLogger(__name__)


ESG_SYSTEM_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert ESG (Environmental, Social, and Governance) analyst with deep knowledge
of sustainability frameworks including GRI, SASB, TCFD, CDP, and UN SDGs.

Use the following ESG document context to answer the question with precision.
Apply chain-of-thought reasoning: first identify the relevant sustainability metric or framework,
then synthesise the evidence, then provide a structured analysis.

Context:
{context}

Question: {question}

Provide a structured ESG analysis with:
1. Key findings from the documents
2. Relevant ESG framework alignment
3. Sustainability metrics and performance indicators
4. Risk and opportunity assessment
5. Recommendations (if applicable)

Answer:"""
)


class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBED_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.llm_openai = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
        self.llm_anthropic = ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
        self.vectorstore: Optional[FAISS] = None
        self._load_or_create_index()

    def _load_or_create_index(self):
        index_path = Path(settings.FAISS_INDEX_PATH)
        if index_path.exists():
            logger.info("Loading existing FAISS index from %s", index_path)
            self.vectorstore = FAISS.load_local(
                str(index_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            docs_path = Path(settings.DOCUMENTS_PATH)
            if docs_path.exists() and any(docs_path.iterdir()):
                logger.info("Building FAISS index from documents at %s", docs_path)
                self._build_index(str(docs_path))
            else:
                logger.warning("No documents found; index not built.")

    def _build_index(self, docs_path: str):
        loader = DirectoryLoader(
            docs_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
        )
        documents = loader.load()

        txt_loader = DirectoryLoader(
            docs_path,
            glob="**/*.txt",
            loader_cls=TextLoader,
        )
        documents += txt_loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(documents)
        logger.info("Split %d documents into %d chunks", len(documents), len(chunks))

        self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
        index_path = Path(settings.FAISS_INDEX_PATH)
        index_path.mkdir(parents=True, exist_ok=True)
        self.vectorstore.save_local(str(index_path))
        logger.info("FAISS index saved to %s", index_path)

    def add_documents(self, file_paths: List[str]) -> int:
        all_chunks = []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        for fp in file_paths:
            if fp.endswith(".pdf"):
                loader = PyPDFLoader(fp)
            else:
                loader = TextLoader(fp)
            docs = loader.load()
            all_chunks.extend(splitter.split_documents(docs))

        if self.vectorstore is None:
            self.vectorstore = FAISS.from_documents(all_chunks, self.embeddings)
        else:
            self.vectorstore.add_documents(all_chunks)

        index_path = Path(settings.FAISS_INDEX_PATH)
        index_path.mkdir(parents=True, exist_ok=True)
        self.vectorstore.save_local(str(index_path))
        return len(all_chunks)

    def query(self, question: str, use_anthropic: bool = False) -> dict:
        if self.vectorstore is None:
            return {
                "answer": "No documents indexed yet. Please upload ESG documents first.",
                "sources": [],
                "model": "none",
            }

        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.TOP_K_RESULTS},
        )
        llm = self.llm_anthropic if use_anthropic else self.llm_openai
        model_name = settings.ANTHROPIC_MODEL if use_anthropic else settings.LLM_MODEL

        chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": ESG_SYSTEM_PROMPT},
        )
        result = chain.invoke({"query": question})
        sources = [
            {
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", 0),
                "excerpt": doc.page_content[:300],
            }
            for doc in result.get("source_documents", [])
        ]
        return {
            "answer": result["result"],
            "sources": sources,
            "model": model_name,
        }

    def get_index_stats(self) -> dict:
        if self.vectorstore is None:
            return {"total_vectors": 0, "status": "empty"}
        return {
            "total_vectors": self.vectorstore.index.ntotal,
            "status": "ready",
            "index_path": settings.FAISS_INDEX_PATH,
        }


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
