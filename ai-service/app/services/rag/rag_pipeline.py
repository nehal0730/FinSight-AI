"""
RAG Pipeline Orchestrator - Unified interface for RAG operations.

Workflow:
1. Index phase: PDF -> chunks -> embeddings -> vector store
2. Query phase: query -> embedding -> retrieval -> LLM -> response

Philosophy:
- Single entry point for all RAG operations
- Handle both indexing and querying
- Track performance metrics
- Provide detailed logging
- Stateful management of documents
"""

import time
from typing import List, Optional
import numpy as np
import os

from app.config.rag_config import RAGSystemConfig, get_rag_config
from app.services.rag.chunking import DocumentChunker, Chunk
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vector_store import FAISSVectorStore
from app.services.rag.retriever import Retriever, RetrievedChunk
from app.services.rag.prompt_engine import PromptEngine, PromptContext, ResponseFormatter
from app.utils.logging import api_logger


class RAGPipeline:
    """
    Production RAG pipeline orchestrating all components.
    
    Usage:
        pipeline = RAGPipeline(config)
        
        # Index a document
        pipeline.index_document(
            text=pdf_text,
            document_id="doc_123",
            page_ranges=[(1, "page1_text"), ...]
        )
        
        # Query
        response = pipeline.query(
            query="What are the main risks?",
            document_id="doc_123"
        )
    """
    
    def __init__(self, config: Optional[RAGSystemConfig] = None):
        """
        Initialize RAG pipeline.
        
        Args:
            config: RAGSystemConfig (uses production preset if None)
        """
        self.config = config or get_rag_config()
        self.config.validate()
        
        # Initialize components
        self.chunker = DocumentChunker(
            chunk_size=self.config.chunking.chunk_size,
            chunk_overlap=self.config.chunking.chunk_overlap
        )
        
        self.embedding_service = EmbeddingService(self.config.embedding)
        
        self.vector_store = FAISSVectorStore(
            storage_dir=self.config.vector_store_root,
            embedding_dim=self.embedding_service.get_embedding_dim()
        )
        
        self.retriever = Retriever(
            config=self.config.retrieval,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store
        )
        
        api_logger.info(
            f"RAG Pipeline initialized: "
            f"chunks={self.config.chunking.chunk_size}, "
            f"embedding={self.config.embedding.model.value}, "
            f"top_k={self.config.retrieval.top_k}"
        )
    
    def index_document(
        self,
        text: str,
        document_id: str,
        page_ranges: Optional[List[tuple]] = None,
        force_reindex: bool = False
    ) -> dict:
        """
        Index a document for RAG.
        
        Full pipeline:
        1. Chunk document
        2. Embed chunks
        3. Store in vector DB
        4. Return indexing stats
        
        Args:
            text: Document text
            document_id: Unique document ID
            page_ranges: Optional page-number metadata
            force_reindex: Re-index even if already indexed
        
        Returns:
            Dict with indexing statistics
        """
        start_time = time.time()
        
        # Check if already indexed
        if (not force_reindex and 
            self.vector_store.document_exists(document_id)):
            api_logger.info(f"Document already indexed: {document_id}")
            return {
                "document_id": document_id,
                "status": "already_indexed",
                "message": f"Document {document_id} is already in vector store"
            }
        
        # Delete old index if force-reindexing
        if force_reindex and self.vector_store.document_exists(document_id):
            self.vector_store.delete_document(document_id)
            api_logger.info(f"Deleted old index for {document_id}")
        
        try:
            # Step 1: Chunking
            api_logger.info(f"Chunking document: {document_id}")
            chunks = self.chunker.chunk_document(text, document_id, page_ranges)
            
            if not chunks:
                return {
                    "document_id": document_id,
                    "status": "error",
                    "error": "No chunks created from document"
                }
            
            api_logger.info(f"Created {len(chunks)} chunks")
            
            # Step 2: Embedding
            api_logger.info(f"Embedding {len(chunks)} chunks")
            embeddings = self.embedding_service.embed_chunks(
                chunks=chunks,
                document_id=document_id,
                force_refresh=force_reindex
            )
            
            if not embeddings:
                return {
                    "document_id": document_id,
                    "status": "error",
                    "error": "Failed to embed chunks"
                }
            
            # Step 3: Vector Store
            api_logger.info(f"Adding to vector store")
            success = self.vector_store.add_documents(chunks, embeddings)
            
            if not success:
                return {
                    "document_id": document_id,
                    "status": "error",
                    "error": "Failed to add to vector store"
                }
            
            # Get stats
            elapsed = time.time() - start_time
            stats = self.vector_store.get_stats(document_id)
            stats.update({
                "status": "success",
                "chunks_created": len(chunks),
                "chunks_embedded": len(embeddings),
                "indexing_time_sec": elapsed
            })
            
            api_logger.info(f"Successfully indexed {document_id} in {elapsed:.2f}s")
            return stats
        
        except Exception as e:
            api_logger.error(f"Indexing failed for {document_id}: {e}", exc_info=True)
            return {
                "document_id": document_id,
                "status": "error",
                "error": str(e)
            }
    
    def query(
        self,
        query: str,
        document_id: str,
        top_k: Optional[int] = None
    ) -> dict:
        """
        Query a document using RAG.
        
        Workflow:
        1. Verify document is indexed
        2. Retrieve relevant chunks
        3. Build prompt with context
        4. Call LLM
        5. Format response
        
        Args:
            query: User query
            document_id: Document to query
            top_k: Override config top_k
        
        Returns:
            Structured RAG response
        """
        start_time = time.time()
        
        try:
            # Verify document exists
            if not self.vector_store.document_exists(document_id):
                return ResponseFormatter.format_error_response(
                    query=query,
                    error_message=f"Document {document_id} not indexed",
                    error_code="DOCUMENT_NOT_FOUND"
                )
            
            api_logger.info(f"Querying {document_id}: {query[:100]}")
            
            # Retrieve chunks
            retrieved = self.retriever.retrieve(
                query=query,
                document_id=document_id,
                top_k=top_k
            )
            
            if not retrieved:
                return ResponseFormatter.format_error_response(
                    query=query,
                    error_message="No relevant chunks found in document",
                    error_code="NO_RESULTS"
                )
            
            api_logger.info(f"Retrieved {len(retrieved)} chunks")
            
            # Build prompt context
            prompt_context = PromptContext(
                query=query,
                retrieved_chunks=retrieved,
                document_name=document_id
            )
            
            # Build messages for LLM
            messages = PromptEngine.build_messages(prompt_context)
            
            # Call LLM (placeholder - integrate with OpenAI/Gemini)
            llm_response = self._call_llm(messages)
            
            # Parse response
            parsed = PromptEngine.parse_response(llm_response)
            
            # Format final response
            latency_ms = (time.time() - start_time) * 1000
            response = ResponseFormatter.format_rag_response(
                query=query,
                answer=parsed["answer"],
                source=parsed["source"],
                confidence=parsed["confidence"],
                context=parsed["context"],
                retrieved_chunks=retrieved,
                latency_ms=latency_ms
            )
            
            api_logger.info(f"Query completed in {latency_ms:.0f}ms")
            return response
        
        except Exception as e:
            api_logger.error(f"Query failed: {e}", exc_info=True)
            error_code = "CONFIG_ERROR" if "GROQ_API_KEY" in str(e) else "QUERY_FAILED"
            return ResponseFormatter.format_error_response(
                query=query,
                error_message=str(e),
                error_code=error_code
            )
    
    def _call_llm(self, messages: List[dict]) -> str:
        """
        Call Groq LLM with prompt messages.
        
        Uses: Groq API (FREE tier - Llama 3 or Mixtral)
        Requires: GROQ_API_KEY environment variable
        
        Args:
            messages: List of message dicts (role + content)
        
        Returns:
            LLM response text
        """
        try:
            groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not groq_api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is missing in ai-service environment. "
                    "Set GROQ_API_KEY and restart uvicorn."
                )

            # Groq API (FREE, Llama3/Mixtral)
            # Use GROQ_API_KEY from environment
            from groq import Groq
            
            client = Groq(api_key=groq_api_key)
            
            response = client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
            
            return response.choices[0].message.content
        
        except ImportError as e:
            api_logger.warning(f"Groq not installed: {e}, returning mock response")
            return self._mock_llm_response()
        except Exception as e:
            api_logger.error(f"LLM call failed: {e}")
            raise
    
    @staticmethod
    def _mock_llm_response() -> str:
        """Return mock response for testing."""
        return """- **Answer:** Based on the retrieved document sections, the information appears to indicate [specific data from context].
- **Source:** Financial Summary section, page 2-3
- **Confidence:** MEDIUM
- **Context:** This information is extracted from multiple document sections and synthesized based on the most relevant retrieved segments."""
    
    def get_document_stats(self, document_id: str) -> dict:
        """Get statistics for an indexed document."""
        return self.vector_store.get_stats(document_id)
    
    def list_documents(self) -> List[str]:
        """List all indexed documents."""
        return self.vector_store.list_documents()
    
    def delete_document(self, document_id: str) -> bool:
        """Delete an indexed document."""
        return self.vector_store.delete_document(document_id)
