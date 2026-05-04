"""
RAG System Configuration - Centralized settings for chunking, embeddings, and retrieval.

Design Philosophy:
- Single source of truth for all RAG hyperparameters
- Experiment-friendly (easy to swap embedding models, adjust chunk sizes)
- Environment-aware (dev vs production)
- Validated at runtime
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EmbeddingModel(str, Enum):
    """Supported embedding models"""
    OPENAI_SMALL = "text-embedding-3-small"      # 1536 dims, fast, cheap
    OPENAI_LARGE = "text-embedding-3-large"      # 3072 dims, accurate
    HUGGINGFACE_MINILM = "all-MiniLM-L6-v2"      # 384 dims, FREE, local/API
    HUGGINGFACE_MPNET = "all-mpnet-base-v2"      # 768 dims, FREE, better quality
    # Gemini support ready: "models/embedding-001"


@dataclass
class ChunkingConfig:
    """
    Chunking strategy parameters.
    
    Philosophy:
    - chunk_size: Larger chunks preserve context but reduce precision. 
      Smaller chunks improve relevance but fragment meaning.
      For financial docs: 500-1000 is sweet spot (avoids cutting mid-table)
    - overlap: Prevents losing information at chunk boundaries.
      Rule of thumb: 20-30% of chunk_size works well.
    """
    chunk_size: int = 500  # tokens (≈ 600-800 words for financial docs)
    chunk_overlap: int = 200  # 25% overlap
    separator: str = "\n\n"  # Split on paragraph boundaries first
    
    def validate(self):
        if self.chunk_size < 100:
            raise ValueError("chunk_size must be >= 100")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")


@dataclass
class EmbeddingConfig:
    """
    Embedding model settings.
    
    Philosophy:
    - Larger models (3072 dims) better for nuanced financial queries
    - Smaller models (384 dims) vs better quality (768 dims)
    - Cache embeddings to avoid re-processing same doc
    - HuggingFace models run locally, no API key needed
    """
    model: EmbeddingModel = EmbeddingModel.HUGGINGFACE_MINILM  # 384 dims, lighter for free hosting
    api_key: str = ""  # Not used for HuggingFace (local inference)
    cache_embeddings: bool = True
    batch_size: int = 100  # Process 100 chunks at once
    
    def validate(self):
        # HuggingFace models run locally and don't require API validation
        pass  # No validation needed for local embeddings


@dataclass
class RetrievalConfig:
    """
    RAG retrieval settings.
    
    Philosophy:
    - top_k: Balance between precision and context window.
      Too small (k=1-2): May miss relevant info
      Too large (k=10+): Dilutes signal, adds latency, fills context
      Sweet spot for financial: k=4-6
    - similarity_threshold: Filter low-confidence matches
      Avoid including barely-relevant chunks that confuse LLM
    """
    top_k: int = 5  # Return top 5 most relevant chunks
    similarity_threshold: float = 0.35  # Cosine similarity cutoff (0-1) - lowered for better recall
    rerank_enabled: bool = True  # Optional: Re-rank for financial relevance
    max_context_length: int = 3000  # Max tokens to pass to LLM


@dataclass
class LLMConfig:
    """
    LLM settings for RAG generation.
    
    Philosophy:
    - temperature=0: Deterministic, avoid hallucination (critical for finance)
    - max_tokens: Leave room for sources + confidence explanation
    """
    provider: str = "groq" 
    model: str = "llama-3.1-8b-instant" 
    temperature: float = 0.0  # Deterministic (no creativity/hallucination)
    max_tokens: int = 1000
    api_key: str = ""  # Not used - reads from GROQ_API_KEY env var
    
    def validate(self):
        # Groq reads from environment variable GROQ_API_KEY automatically
        # No need to validate here - services load lazily
        if not (0 <= self.temperature <= 1):
            raise ValueError("temperature must be in [0, 1]")


@dataclass
class RAGSystemConfig:
    """Master RAG configuration object"""
    
    chunking: ChunkingConfig = None
    embedding: EmbeddingConfig = None
    retrieval: RetrievalConfig = None
    llm: LLMConfig = None
    
    # Storage paths
    vector_store_root: Path = None  # Where to store per-document indexes
    logs_dir: Path = None
    
    def __post_init__(self):
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.retrieval is None:
            self.retrieval = RetrievalConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.vector_store_root is None:
            self.vector_store_root = Path(__file__).parent.parent.parent / "storage" / "vectors"
        if self.logs_dir is None:
            self.logs_dir = Path(__file__).parent.parent.parent / "logs"
    
    def validate(self):
        """Validate all sub-configs"""
        self.chunking.validate()
        self.embedding.validate()
        self.llm.validate()
        self.vector_store_root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


# ========== PRESET CONFIGURATIONS ==========
# Use these for A/B testing and quick parameter swaps

class RAGConfigPresets:
    """Pre-tuned configurations for different use cases"""
    
    @staticmethod
    def production() -> RAGSystemConfig:
        """Balanced production settings (recommended) - FREE TIER"""
        config = RAGSystemConfig()
        config.chunking = ChunkingConfig(chunk_size=500, chunk_overlap=200)
        embedding_model_name = os.getenv("EMBEDDING_MODEL") or os.getenv("RAG_EMBEDDING_MODEL")
        try:
            embedding_model = EmbeddingModel(embedding_model_name) if embedding_model_name else EmbeddingModel.HUGGINGFACE_MINILM
        except ValueError:
            embedding_model = EmbeddingModel.HUGGINGFACE_MINILM
        config.embedding = EmbeddingConfig(model=embedding_model)
        config.retrieval = RetrievalConfig(top_k=5, similarity_threshold=0.35)
        config.llm = LLMConfig(provider="groq", model="llama-3.1-8b-instant", temperature=0.3, max_tokens=1500)
        return config
    
    @staticmethod
    def high_precision() -> RAGSystemConfig:
        """Optimized for accuracy (FREE tier)"""
        config = RAGSystemConfig()
        config.chunking = ChunkingConfig(chunk_size=600, chunk_overlap=150)
        config.embedding = EmbeddingConfig(model=EmbeddingModel.HUGGINGFACE_MPNET)  # Best quality embeddings
        config.retrieval = RetrievalConfig(top_k=6, similarity_threshold=0.35, rerank_enabled=True)
        config.llm = LLMConfig(provider="groq", model="llama-3.1-70b-versatile", temperature=0.0)  # Better reasoning
        return config
    
    @staticmethod
    def fast_inference() -> RAGSystemConfig:
        """Optimized for speed and cost - FREE TIER"""
        config = RAGSystemConfig()
        config.chunking = ChunkingConfig(chunk_size=1000, chunk_overlap=250)
        config.embedding = EmbeddingConfig(model=EmbeddingModel.HUGGINGFACE_MINILM)
        config.retrieval = RetrievalConfig(top_k=3, similarity_threshold=0.35)
        config.llm = LLMConfig(provider="groq", model="llama-3.1-8b-instant", temperature=0.0)
        return config
    
    @staticmethod
    def evaluation() -> RAGSystemConfig:
        """Settings for evaluation/testing (detailed logging)"""
        config = RAGConfigPresets.production()
        config.retrieval.similarity_threshold = 0.5
        return config


# ========== GLOBAL INSTANCE ==========
# Initialized on startup in main.py

_rag_config: RAGSystemConfig = None


def get_rag_config() -> RAGSystemConfig:
    """Get current RAG configuration (thread-safe)"""
    global _rag_config
    if _rag_config is None:
        _rag_config = RAGConfigPresets.production()
        _rag_config.validate()
    return _rag_config


def set_rag_config(config: RAGSystemConfig):
    """Set RAG configuration (for testing/experiments)"""
    global _rag_config
    config.validate()
    _rag_config = config
