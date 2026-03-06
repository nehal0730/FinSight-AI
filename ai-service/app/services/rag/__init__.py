"""RAG Service Package - Production-grade RAG system for financial documents."""

from app.services.rag.chunking import DocumentChunker, Chunk
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vector_store import FAISSVectorStore
from app.services.rag.retriever import Retriever, RetrievedChunk
from app.services.rag.rag_pipeline import RAGPipeline
from app.services.rag.evaluator import RAGEvaluator

__all__ = [
    "DocumentChunker",
    "Chunk",
    "EmbeddingService",
    "FAISSVectorStore",
    "Retriever",
    "RetrievedChunk",
    "RAGPipeline",
    "RAGEvaluator",
]
