"""
Embeddings Module - Vectorize text using OpenAI or Gemini APIs with caching.

Philosophy:
- Cache embeddings to avoid re-processing same documents
- Batch API calls for efficiency
- Support multiple embedding models for A/B testing
- Track embedding costs and performance

Embedding Models:
- text-embedding-3-small: 1536 dims, fast, cheap (recommended for MVP)
- text-embedding-3-large: 3072 dims, more accurate (recommended for production)
- Gemini embedding-001: Alternative for cost-sensitive scenarios
"""

import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import numpy as np
import os

from app.config.rag_config import EmbeddingConfig, EmbeddingModel
from app.utils.logging import api_logger


class EmbeddingCache:
    """
    Simple file-based cache for embeddings.
    
    Design:
    - Cache file per document ID
    - Store as JSON with text->vector mapping
    - Check cache before API calls
    - Reduce costs and latency significantly
    """
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, document_id: str, model: str) -> Path:
        """Get cache file path for document + model combination."""
        safe_model = model.replace("/", "_")
        return self.cache_dir / f"{document_id}_{safe_model}.json"
    
    def get(self, text: str, document_id: str, model: str) -> Optional[np.ndarray]:
        """
        Retrieve cached embedding for text.
        
        Args:
            text: Original text to embed
            document_id: Source document ID
            model: Embedding model name
        
        Returns:
            Embedding vector if cached, None otherwise
        """
        cache_path = self.get_cache_path(document_id, model)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Use text hash as key
            text_hash = self._hash_text(text)
            if text_hash in cache_data:
                return np.array(cache_data[text_hash], dtype=np.float32)
            return None
        except Exception as e:
            api_logger.error(f"Embedding cache read error: {e}")
            return None
    
    def set(self, text: str, embedding: List[float], document_id: str, model: str):
        """Cache embedding for text."""
        cache_path = self.get_cache_path(document_id, model)
        
        try:
            # Load existing cache
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
            
            # Add new embedding
            text_hash = self._hash_text(text)
            cache_data[text_hash] = embedding
            
            # Save
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
        except Exception as e:
            api_logger.error(f"Embedding cache write error: {e}")
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Create consistent hash of text."""
        return hashlib.md5(text.encode()).hexdigest()


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""
    
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts, return list of vectors."""
        pass
    
    @abstractmethod
    def get_embedding_dim(self) -> int:
        """Return dimension of embedding vectors."""
        pass


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    HuggingFace Sentence Transformers embedding provider.
    
    FREE, runs locally. No API key needed. Models download once and cache locally.
    """
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        
        # Download model (cached after first run)
        api_logger.info(f"Loading HuggingFace model: {model}")
        self.model = SentenceTransformer(model)
        self.model_name = model
        api_logger.info(f"Model loaded successfully")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding using sentence-transformers (local)."""
        if not texts:
            return []
        
        try:
            # Encode returns numpy array
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Convert to list of lists
            return embeddings.tolist()
        except Exception as e:
            api_logger.error(f"HuggingFace embedding error: {e}")
            raise
    
    def get_embedding_dim(self) -> int:
        """Return embedding dimension."""
        if "MiniLM" in self.model_name:
            return 384
        elif "mpnet" in self.model_name:
            return 768
        else:
            # Get dimension from model
            return self.model.get_sentence_embedding_dimension()


class EmbeddingService:
    """
    High-level embedding service with HuggingFace (FREE, local).
    
    Workflow:
    1. Check cache for existing embeddings
    2. Batch texts that need embedding
    3. Call HuggingFace provider
    4. Cache results
    5. Return complete vector list
    """
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        
        # Initialize HuggingFace provider (always)
        self.provider = HuggingFaceEmbeddingProvider(
            model=config.model.value
        )
        
        # Initialize cache
        cache_dir = Path(__file__).parent.parent.parent.parent / "storage" / "embeddings"
        self.cache = EmbeddingCache(cache_dir) if config.cache_embeddings else None
        
        api_logger.info(f"Embedding service initialized: {config.model.value}")
    
    def embed_chunks(
        self,
        chunks: List,  # List of Chunk objects
        document_id: str,
        force_refresh: bool = False
    ) -> dict:
        """
        Embed document chunks with smart caching.
        
        Args:
            chunks: List of Chunk objects to embed
            document_id: Document identifier for caching
            force_refresh: Skip cache and re-embed
        
        Returns:
            Dictionary mapping chunk_id -> embedding_vector
        """
        embeddings_map = {}
        to_embed = []
        to_embed_indices = []
        
        # Check cache for each chunk
        for i, chunk in enumerate(chunks):
            if not force_refresh and self.cache:
                cached = self.cache.get(chunk.content, document_id, self.config.model.value)
                if cached is not None:
                    embeddings_map[chunk.chunk_id] = cached
                    api_logger.debug(f"Cache hit: {chunk.chunk_id}")
                    continue
            
            to_embed.append(chunk.content)
            to_embed_indices.append(i)
        
        # Embed uncached chunks in batches
        if to_embed:
            api_logger.info(f"Embedding {len(to_embed)} chunks (cache miss: {len(to_embed)}/{len(chunks)})")
            
            for batch_start in range(0, len(to_embed), self.config.batch_size):
                batch_end = min(batch_start + self.config.batch_size, len(to_embed))
                batch = to_embed[batch_start:batch_end]
                
                # Call provider
                batch_embeddings = self.provider.embed_texts(batch)
                
                # Store in map and cache
                for j, embedding in enumerate(batch_embeddings):
                    chunk_idx = to_embed_indices[batch_start + j]
                    chunk = chunks[chunk_idx]
                    
                    embedding_array = np.array(embedding, dtype=np.float32)
                    embeddings_map[chunk.chunk_id] = embedding_array
                    
                    # Cache for next time
                    if self.cache:
                        self.cache.set(chunk.content, embedding, document_id, self.config.model.value)
        
        api_logger.info(f"Successfully embedded {len(embeddings_map)} chunks")
        return embeddings_map
    
    def get_embedding_dim(self) -> int:
        """Get dimension of embeddings from provider."""
        return self.provider.get_embedding_dim()
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string.
        This is critical for retrieval!
        
        Args:
            query: User query text
        
        Returns:
            Embedding vector (normalized for cosine similarity)
        """
        embedding = self.provider.embed_texts([query])[0]
        return np.array(embedding, dtype=np.float32)
