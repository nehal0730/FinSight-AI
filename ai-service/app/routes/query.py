"""
Query Endpoint - FastAPI route for RAG queries against indexed documents.

Endpoints:
- POST /query - Query an indexed document
- POST /query/batch - Query multiple queries
- GET /documents - List indexed documents
- GET /documents/{doc_id}/stats - Get document statistics
- DELETE /documents/{doc_id} - Delete indexed document
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import time

from app.services.rag.rag_pipeline import RAGPipeline
from app.config.rag_config import get_rag_config
from app.utils.logging import api_logger, request_id_var, PerformanceTimer

router = APIRouter(prefix="/query", tags=["rag"])

# Global RAG pipeline (initialized once)
_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or initialize RAG pipeline."""
    global _pipeline
    if _pipeline is None:
        config = get_rag_config()
        _pipeline = RAGPipeline(config)
    return _pipeline


# ========== REQUEST/RESPONSE MODELS ==========

class QueryRequest(BaseModel):
    """Single query request."""
    query: str
    document_id: str
    top_k: Optional[int] = None  # Optional override


class BatchQueryRequest(BaseModel):
    """Batch query request."""
    queries: list[str]
    document_id: str
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    """Query response (matches RAGPipeline output)."""
    query: str
    answer: str
    source: str
    confidence: str
    context: str
    citations: list[dict]
    metrics: dict
    error: dict = None


class DocumentStatsResponse(BaseModel):
    """Document statistics."""
    document_id: str
    chunk_count: int
    total_characters: int
    total_words: int
    avg_chunk_size: float


# ========== ENDPOINTS ==========

@router.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    """
    Query an indexed document using RAG.
    
    Args:
        request: QueryRequest with query and document_id
    
    Returns:
        QueryResponse with answer, sources, and confidence
    
    Raises:
        404: Document not found
        400: Invalid request
    """
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)
    
    with PerformanceTimer(api_logger, f"Query: {request.query[:50]}"):
        try:
            if not request.query or not request.query.strip():
                raise HTTPException(status_code=400, detail="Query cannot be empty")
            
            if not request.document_id:
                raise HTTPException(status_code=400, detail="document_id required")
            
            api_logger.info(f"Query request: {request.query[:80]}")
            
            pipeline = get_rag_pipeline()
            response = pipeline.query(
                query=request.query,
                document_id=request.document_id,
                top_k=request.top_k
            )
            
            # Check for errors in response
            if "error" in response:
                error_code = response["error"].get("code", "QUERY_FAILED")
                status_map = {
                    "DOCUMENT_NOT_FOUND": 404,
                    "NO_RESULTS": 404,
                    "CONFIG_ERROR": 500,
                    "QUERY_FAILED": 500,
                }
                raise HTTPException(
                    status_code=status_map.get(error_code, 500),
                    detail=response["error"]["message"]
                )
            
            return response
        
        except HTTPException:
            raise
        except Exception as e:
            api_logger.error(f"Query failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/batch")
async def batch_query(request: BatchQueryRequest):
    """
    Query multiple prompts against a document.
    
    Args:
        request: BatchQueryRequest with list of queries
    
    Returns:
        List of QueryResponse objects
    """
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)
    
    try:
        if not request.queries:
            raise HTTPException(status_code=400, detail="queries list cannot be empty")
        
        api_logger.info(f"Batch query: {len(request.queries)} queries")
        
        pipeline = get_rag_pipeline()
        responses = [
            pipeline.query(
                query=q,
                document_id=request.document_id,
                top_k=request.top_k
            )
            for q in request.queries
        ]
        
        return responses
    
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Batch query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents():
    """
    List all indexed documents.
    
    Returns:
        List of document IDs
    """
    try:
        pipeline = get_rag_pipeline()
        docs = pipeline.list_documents()
        
        return {
            "documents": docs,
            "count": len(docs)
        }
    
    except Exception as e:
        api_logger.error(f"List documents failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/stats")
async def get_document_stats(document_id: str):
    """
    Get statistics for an indexed document.
    
    Args:
        document_id: Document ID
    
    Returns:
        Document statistics (chunk count, size, etc.)
    """
    try:
        pipeline = get_rag_pipeline()
        stats = pipeline.get_document_stats(document_id)
        
        if "status" in stats and stats["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Get stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete an indexed document and its vector index.
    
    Args:
        document_id: Document ID to delete
    
    Returns:
        Confirmation message
    """
    try:
        api_logger.info(f"Deleting document: {document_id}")
        
        pipeline = get_rag_pipeline()
        success = pipeline.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        return {
            "message": f"Document {document_id} deleted successfully",
            "document_id": document_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Delete failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
