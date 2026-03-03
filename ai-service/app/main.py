from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.analyze import router as analyze_router
from app.utils.logging import api_logger


app = FastAPI(
    title="FinSight AI Service",
    version="2.0.0",
    description="Production-grade PDF analysis with financial pattern detection and compliance flagging",
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

# ========== Startup Event ==========

@app.on_event("startup")
async def startup_event():
    """Log service startup"""
    api_logger.info("FinSight AI Service started successfully")

# ========== Shutdown Event ==========

@app.on_event("shutdown")
async def shutdown_event():
    """Log service shutdown"""
    api_logger.info("FinSight AI Service shutting down")
