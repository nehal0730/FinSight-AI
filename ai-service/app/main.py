from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

from app.routes.analyze import router as analyze_router
from app.routes.query import router as query_router
from app.routes.risk_analysis import router as risk_analysis_router
from app.routes.fraud_detect import router as fraud_detect_router
from app.config.rag_config import get_rag_config
from app.services.rag.rag_pipeline import RAGPipeline
from app.utils.logging import api_logger


def _load_local_env_file():
    """Load key=value pairs from ai-service/.env if present."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env_file()


app = FastAPI(
    title="FinSight AI Service",
    version="3.0.0",
    description="Production-grade RAG system with PDF analysis, pattern detection, and financial QA",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ========== CORS Middleware (for frontend integration) ==========

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5000",  # Node backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Service status and version info
    """
    return {
        "status": "UP",
        "service": "FinSight AI Service",
        "version": "2.0.0"
    }

# ========== API Routes ==========

app.include_router(analyze_router)
app.include_router(query_router)
app.include_router(risk_analysis_router)
app.include_router(fraud_detect_router)

# ========== Startup Event ==========

@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline and log service startup"""
    try:
        # Initialize RAG pipeline with production config
        config = get_rag_config()
        config.validate()
        
        # Pre-initialize pipeline
        from app.routes.query import get_rag_pipeline
        pipeline = get_rag_pipeline()
        
        api_logger.info("RAG Pipeline initialized successfully")
        api_logger.info(f"  - Chunking: {config.chunking.chunk_size} tokens")
        api_logger.info(f"  - Embeddings: {config.embedding.model.value}")
        api_logger.info(f"  - Retrieval: top_k={config.retrieval.top_k}")
        api_logger.info(f"  - LLM: {config.llm.model}")
    except Exception as e:
        api_logger.error(f"RAG Pipeline initialization failed: {e}", exc_info=True)
    
    api_logger.info("FinSight AI Service started successfully")

# ========== Shutdown Event ==========

@app.on_event("shutdown")
async def shutdown_event():
    """Log service shutdown"""
    api_logger.info("FinSight AI Service shutting down")
