"""
Vector Store Module - FAISS-based persistent vector database.

Architecture:
- One vector database per document (allows efficient deletion, updating)
- Store index + metadata separately
- Metadata includes original chunks, page numbers, source info
- Disk-persistent for stateless API design

Philosophy:
- FAISS provides fast similarity search via approximate NN
- Metadata kept in JSON for reconstruction of original chunks
- Per-document indexing prevents re-embedding existing docs
- Supports millions of vectors efficiently
"""

import json
import pickle
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from app.services.rag.chunking import Chunk
from app.utils.logging import api_logger


class FAISSVectorStore:
    """
    FAISS-based vector store with persistent metadata.
    
    File structure per document:
    - {document_id}.faiss: FAISS index (binary)
    - {document_id}_meta.json: Chunk metadata (text, page, section, etc.)
    - {document_id}_chunks.pkl: Raw Chunk objects (for reconstruction)
    """
    
    def __init__(self, storage_dir: Path, embedding_dim: int):
        """
        Initialize vector store.
        
        Args:
            storage_dir: Directory to store indexes and metadata
            embedding_dim: Dimension of embedding vectors
        """
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu or faiss-gpu")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        
        # In-memory indexes (loaded on demand)
        self._indexes = {}  # document_id -> faiss.IndexFlatL2
        self._metadata = {}  # document_id -> list of metadata dicts
        self._chunks = {}    # document_id -> list of Chunk objects
    
    def get_index_path(self, document_id: str) -> Path:
        """Get FAISS index file path."""
        return self.storage_dir / f"{document_id}.faiss"
    
    def get_metadata_path(self, document_id: str) -> Path:
        """Get metadata file path."""
        return self.storage_dir / f"{document_id}_meta.json"
    
    def get_chunks_path(self, document_id: str) -> Path:
        """Get serialized chunks file path."""
        return self.storage_dir / f"{document_id}_chunks.pkl"
    
    def add_documents(self, chunks: List[Chunk], embeddings: dict) -> bool:
        """
        Add document chunks with their embeddings to the vector store.
        
        Args:
            chunks: List of Chunk objects
            embeddings: Dict mapping chunk_id -> embedding_vector (np.ndarray)
        
        Returns:
            True if successful
        """
        if not chunks or not embeddings:
            api_logger.warning("No chunks or embeddings to add")
            return False
        
        document_id = chunks[0].document_id
        
        # Create FAISS index
        index = faiss.IndexFlatL2(self.embedding_dim)  # L2 distance (Euclidean)
        
        # Add embeddings in order
        embedding_vectors = []
        metadata_list = []
        
        for chunk in chunks:
            if chunk.chunk_id not in embeddings:
                api_logger.warning(f"No embedding for {chunk.chunk_id}")
                continue
            
            embedding = embeddings[chunk.chunk_id]
            # Normalize L2 for better distance computation
            embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
            embedding_vectors.append(embedding_norm)
            
            # Store metadata
            metadata_list.append({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "position": chunk.position,
                "metadata": chunk.metadata
            })
        
        if not embedding_vectors:
            api_logger.error(f"No valid embeddings for document {document_id}")
            return False
        
        # Add to FAISS
        vectors_array = np.array(embedding_vectors, dtype=np.float32)
        index.add(vectors_array)
        
        # Save index
        index_path = self.get_index_path(document_id)
        faiss.write_index(index, str(index_path))
        
        # Save metadata
        meta_path = self.get_metadata_path(document_id)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=2)
        
        # Save original chunks
        chunks_path = self.get_chunks_path(document_id)
        with open(chunks_path, 'wb') as f:
            pickle.dump(chunks, f)
        
        # Cache in memory
        self._indexes[document_id] = index
        self._metadata[document_id] = metadata_list
        self._chunks[document_id] = chunks
        
        api_logger.info(f"Added {len(chunks)} chunks to vector store: {document_id}")
        return True
    
    def search(
        self,
        query_embedding: np.ndarray,
        document_id: str,
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for most similar chunks in a document.
        
        Args:
            query_embedding: Query embedding vector (normalized)
            document_id: Document to search in
            top_k: Number of results to return
        
        Returns:
            List of (Chunk, similarity_score) tuples
        """
        # Normalize query
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        query_norm = np.array([query_norm], dtype=np.float32)
        
        # Load index if not in memory
        if document_id not in self._indexes:
            self._load_document(document_id)
        
        if document_id not in self._indexes:
            api_logger.warning(f"Document {document_id} not in vector store")
            return []
        
        index = self._indexes[document_id]
        chunks = self._chunks[document_id]
        
        # FAISS returns L2 distances
        distances, indices = index.search(query_norm, min(top_k, index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(chunks):  # -1 indicates no result
                continue
            
            chunk = chunks[int(idx)]
            distance = distances[0][i]
            
            # Convert L2 distance to similarity score (0-1)
            # For L2: similarity ≈ 1 / (1 + distance)
            similarity = 1.0 / (1.0 + float(distance))
            
            results.append((chunk, similarity))
        
        api_logger.debug(f"Search results: {len(results)} chunks for query in {document_id}")
        return results
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all data for a document."""
        paths = [
            self.get_index_path(document_id),
            self.get_metadata_path(document_id),
            self.get_chunks_path(document_id)
        ]
        
        for path in paths:
            if path.exists():
                path.unlink()
        
        # Clear from memory
        self._indexes.pop(document_id, None)
        self._metadata.pop(document_id, None)
        self._chunks.pop(document_id, None)
        
        api_logger.info(f"Deleted document from vector store: {document_id}")
        return True
    
    def document_exists(self, document_id: str) -> bool:
        """Check if document is in vector store."""
        index_path = self.get_index_path(document_id)
        return index_path.exists()
    
    def _load_document(self, document_id: str) -> bool:
        """Load document index and metadata from disk."""
        index_path = self.get_index_path(document_id)
        meta_path = self.get_metadata_path(document_id)
        chunks_path = self.get_chunks_path(document_id)
        
        if not index_path.exists():
            api_logger.warning(f"Index not found for {document_id}")
            return False
        
        try:
            # Load index
            index = faiss.read_index(str(index_path))
            self._indexes[document_id] = index
            
            # Load metadata
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self._metadata[document_id] = json.load(f)
            
            # Load chunks
            if chunks_path.exists():
                with open(chunks_path, 'rb') as f:
                    self._chunks[document_id] = pickle.load(f)
            
            api_logger.info(f"Loaded document from disk: {document_id}")
            return True
        except Exception as e:
            api_logger.error(f"Failed to load document {document_id}: {e}")
            return False
    
    def get_stats(self, document_id: str) -> dict:
        """Get statistics about a document's index."""
        if document_id not in self._indexes:
            self._load_document(document_id)
        
        if document_id not in self._indexes:
            return {"status": "not_found"}
        
        index = self._indexes[document_id]
        chunks = self._chunks.get(document_id, [])
        
        total_chars = sum(len(c.content) for c in chunks)
        total_words = sum(c.word_count() for c in chunks)
        
        return {
            "document_id": document_id,
            "chunk_count": index.ntotal,
            "total_characters": total_chars,
            "total_words": total_words,
            "avg_chunk_size": total_chars / len(chunks) if chunks else 0,
            "embedding_dim": self.embedding_dim
        }
    
    def list_documents(self) -> List[str]:
        """List all indexed documents."""
        documents = set()
        for path in self.storage_dir.glob("*.faiss"):
            doc_id = path.stem
            documents.add(doc_id)
        return sorted(documents)
