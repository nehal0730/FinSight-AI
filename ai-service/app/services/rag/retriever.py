"""
Retriever Module - Convert queries into retrieved chunks with optional re-ranking.

Philosophy:
- Simple retrieval: Dense vector similarity
- Re-ranking (optional): Apply financial-specific heuristics to re-score results
- Confidence estimation: Basic heuristic for answer trustworthiness
- Source tracking: Include metadata for citations

Re-ranking Strategy for Finance:
- Boost chunks with financial entities (amounts, dates, risk keywords)
- Penalize generic/boilerplate text
- Prefer chunks from recent/authoritative sections
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from app.config.rag_config import RetrievalConfig
from app.services.rag.chunking import Chunk
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vector_store import FAISSVectorStore
from app.utils.logging import api_logger


@dataclass
class RetrievedChunk:
    """A chunk returned from retrieval with scoring metadata."""
    chunk: Chunk
    similarity_score: float  # 0-1, from vector distance
    rerank_score: float = None  # Optional re-ranking score
    final_score: float = None  # Combined score
    confidence: float = None  # Confidence in relevance
    
    def __post_init__(self):
        if self.final_score is None:
            self.final_score = self.similarity_score
        if self.confidence is None:
            # Simple heuristic: map similarity to confidence
            self.confidence = min(self.final_score * 1.5, 1.0)  # Amplify confidence signal


class FinancialReRanker:
    """
    Optional re-ranker for financial documents.
    
    Heuristics:
    1. Boost chunks containing financial entities (amounts, percentages)
    2. Boost chunks from key sections (Risk Analysis, Financial Summary)
    3. Penalize generic boilerplate content
    4. Consider chunk freshness/position
    
    This is domain-specific and can be tuned via experiments.
    """
    
    # Keywords that indicate important financial sections
    FINANCIAL_KEYWORDS = {
        "revenue", "profit", "loss", "cash flow", "ebitda", "margin",
        "risk", "exposure", "volatility", "debt", "equity", "return",
        "interest rate", "inflation", "gdp", "index", "fund", "portfolio",
        "dividend", "yield", "credit", "default", "rating", "compliance",
        "regulation", "requirement", "reserve", "capital", "roe", "roa"
    }
    
    BOILERPLATE_KEYWORDS = {
        "all trademarks", "copyright", "disclaimer", "confidential",
        "footnote", "page break", "table of contents", "index",
        "header", "footer", "page number"
    }
    
    @staticmethod
    def rerank(
        retrieved_chunks: List[tuple],  # [(Chunk, similarity_score)]
        query: str,
        enabled: bool = True
    ) -> List[RetrievedChunk]:
        """
        Re-rank retrieved chunks using financial heuristics.
        
        Args:
            retrieved_chunks: List of (Chunk, similarity) from vector search
            query: Original query (for context)
            enabled: Whether to apply re-ranking
        
        Returns:
            List of RetrievedChunk objects with final scores
        """
        if not enabled:
            # Skip re-ranking, just convert to RetrievedChunk
            return [
                RetrievedChunk(chunk=chunk, similarity_score=sim)
                for chunk, sim in retrieved_chunks
            ]
        
        reranked = []
        
        for chunk, sim_score in retrieved_chunks:
            rerank_score = FinancialReRanker._compute_rerank_score(chunk, query)
            
            # Combine similarity and re-ranking (weighted)
            # favor similarity but boost with re-ranking signal
            combined_score = 0.7 * sim_score + 0.3 * rerank_score
            
            retrieved = RetrievedChunk(
                chunk=chunk,
                similarity_score=sim_score,
                rerank_score=rerank_score,
                final_score=combined_score
            )
            reranked.append(retrieved)
        
        # Sort by final score
        reranked.sort(key=lambda x: x.final_score, reverse=True)
        return reranked
    
    @staticmethod
    def _compute_rerank_score(chunk: Chunk, query: str) -> float:
        """
        Compute financial relevance score (0-1).
        
        Strategy:
        - Check for financial entities in chunk
        - Check for boilerplate (penalty)
        - Boost based on section type
        """
        content_lower = chunk.content.lower()
        query_lower = query.lower()
        
        score = 0.5  # Baseline
        
        # Boost for financial keywords
        financial_matches = sum(1 for kw in FinancialReRanker.FINANCIAL_KEYWORDS
                               if kw in content_lower)
        if financial_matches > 0:
            score += min(financial_matches * 0.05, 0.2)
        
        # Penalize boilerplate
        boilerplate_matches = sum(1 for kw in FinancialReRanker.BOILERPLATE_KEYWORDS
                                 if kw in content_lower)
        if boilerplate_matches > 0:
            score -= min(boilerplate_matches * 0.1, 0.3)
        
        # Boost if section title matches query
        if chunk.section_title and query_lower in chunk.section_title.lower():
            score += 0.15
        
        # Chunk length heuristic: very short chunks often less useful
        if len(chunk.content.split()) < 20:
            score *= 0.8
        
        return max(0.0, min(score, 1.0))  # Clamp to [0, 1]


class Retriever:
    """
    Unified retriever orchestrating vector search + optional re-ranking.
    
    Usage:
        retriever = Retriever(config, embedding_service, vector_store)
        results = retriever.retrieve(query, document_id)
        for result in results:
            print(result.chunk.content)
            print(f"Confidence: {result.confidence:.2f}")
    """
    
    def __init__(
        self,
        config: RetrievalConfig,
        embedding_service: EmbeddingService,
        vector_store: FAISSVectorStore
    ):
        self.config = config
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    def retrieve(
        self,
        query: str,
        document_id: str,
        top_k: Optional[int] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve most relevant chunks for a query.
        
        Args:
            query: User query text
            document_id: Document to search
            top_k: Number of results (uses config default if None)
        
        Returns:
            List of RetrievedChunk objects ranked by relevance
        """
        if top_k is None:
            top_k = self.config.top_k
        
        # Embed query
        query_embedding = self.embedding_service.embed_query(query)
        
        # Vector search
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            document_id=document_id,
            top_k=top_k * 2  # Over-fetch for filtering
        )
        
        api_logger.debug(f"Vector search returned {len(raw_results)} chunks")
        
        # Filter by similarity threshold
        filtered = [
            (chunk, sim) for chunk, sim in raw_results
            if sim >= self.config.similarity_threshold
        ]
        
        if not filtered:
            api_logger.warning(f"No chunks passed threshold {self.config.similarity_threshold}")
            return []
        
        api_logger.debug(f"Filtered to {len(filtered)} chunks above threshold")
        
        # Re-rank (optional)
        retrieved_chunks = FinancialReRanker.rerank(
            filtered,
            query,
            enabled=self.config.rerank_enabled
        )
        
        # Return top_k
        top_results = retrieved_chunks[:top_k]
        
        api_logger.info(
            f"Retrieved {len(top_results)} chunks for query in {document_id} "
            f"(scores: {[f'{r.final_score:.3f}' for r in top_results]})"
        )
        
        return top_results
    
    def retrieve_batch(
        self,
        queries: List[str],
        document_id: str
    ) -> List[List[RetrievedChunk]]:
        """
        Retrieve for multiple queries (parallel-friendly).
        
        Args:
            queries: List of queries
            document_id: Document to search
        
        Returns:
            List of result lists
        """
        return [
            self.retrieve(query, document_id)
            for query in queries
        ]
