"""
MongoDB Vector Store - Replaces local FAISS disk storage

Stores FAISS indexes, metadata, and chunks in MongoDB GridFS
- One collection per document
- Index stored as binary in GridFS
- Metadata stored in separate collection
- Supports efficient deletion and updating
"""

import json
import pickle
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import os

try:
    import faiss
except ImportError:
    faiss = None

from app.services.rag.chunking import Chunk
from app.utils.logging import api_logger


class MongoVectorStore:
    """MongoDB-backed vector store using FAISS and GridFS"""
    
    def __init__(self, mongo_uri: str, db_name: str = "finsight", embedding_dim: int = 384):
        """
        Initialize MongoDB vector store.
        
        Args:
            mongo_uri: MongoDB connection string
            db_name: Database name
            embedding_dim: Dimension of embedding vectors
        """
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")
        
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable not set")
        
        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.client.admin.command('ping')
            api_logger.info("✓ Connected to MongoDB")
        except ServerSelectionTimeoutError as e:
            raise RuntimeError(f"Failed to connect to MongoDB: {e}")
        
        self.db = self.client[db_name]
        self.embedding_dim = embedding_dim
        
        # In-memory indexes (loaded on demand)
        self._indexes = {}
        self._metadata = {}
        self._chunks = {}
    
    def add_documents(self, chunks: List[Chunk], embeddings: dict) -> bool:
        """Add document chunks with embeddings to MongoDB"""
        if not chunks or not embeddings:
            api_logger.warning("No chunks or embeddings to add")
            return False
        
        document_id = chunks[0].document_id
        
        try:
            # Create FAISS index
            index = faiss.IndexFlatL2(self.embedding_dim)
            
            embedding_vectors = []
            metadata_list = []
            
            for chunk in chunks:
                if chunk.chunk_id not in embeddings:
                    api_logger.warning(f"No embedding for {chunk.chunk_id}")
                    continue
                
                embedding = embeddings[chunk.chunk_id]
                # Normalize L2
                embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
                embedding_vectors.append(embedding_norm)
                
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
            
            # Serialize index to bytes
            index_bytes = faiss.serialize_index(index)
            chunks_bytes = pickle.dumps(chunks)
            
            # Store in MongoDB
            collection = self.db["vector_indexes"]
            
            collection.update_one(
                {"document_id": document_id},
                {
                    "$set": {
                        "document_id": document_id,
                        "index_data": index_bytes,
                        "metadata": metadata_list,
                        "chunks_data": chunks_bytes,
                        "embedding_dim": self.embedding_dim,
                        "updated_at": np.datetime64('now')
                    }
                },
                upsert=True
            )
            
            # Cache in memory
            self._indexes[document_id] = index
            self._metadata[document_id] = metadata_list
            self._chunks[document_id] = chunks
            
            api_logger.info(f"✓ Added {len(chunks)} chunks to MongoDB vector store: {document_id}")
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to add documents to MongoDB: {e}")
            return False
    
    def search(
        self,
        query_embedding: np.ndarray,
        document_id: str,
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """Search for similar chunks in a document"""
        # Normalize query
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        query_norm = np.array([query_norm], dtype=np.float32)
        
        # Load from MongoDB if not in memory
        if document_id not in self._indexes:
            self._load_document(document_id)
        
        if document_id not in self._indexes:
            api_logger.warning(f"Document {document_id} not in vector store")
            return []
        
        index = self._indexes[document_id]
        chunks = self._chunks[document_id]
        
        distances, indices = index.search(query_norm, min(top_k, index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(chunks):
                continue
            
            chunk = chunks[int(idx)]
            distance = distances[0][i]
            similarity = 1.0 / (1.0 + float(distance))
            
            results.append((chunk, similarity))
        
        api_logger.debug(f"Search results: {len(results)} chunks for query in {document_id}")
        return results
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all data for a document"""
        try:
            collection = self.db["vector_indexes"]
            result = collection.delete_one({"document_id": document_id})
            
            # Clear from memory
            self._indexes.pop(document_id, None)
            self._metadata.pop(document_id, None)
            self._chunks.pop(document_id, None)
            
            api_logger.info(f"✓ Deleted document from MongoDB vector store: {document_id}")
            return result.deleted_count > 0
        except Exception as e:
            api_logger.error(f"Failed to delete document: {e}")
            return False
    
    def document_exists(self, document_id: str) -> bool:
        """Check if document is in vector store"""
        try:
            collection = self.db["vector_indexes"]
            return collection.find_one({"document_id": document_id}) is not None
        except Exception as e:
            api_logger.error(f"Error checking document existence: {e}")
            return False

    def list_documents(self) -> List[str]:
        """List all documents that are actually indexed in MongoDB."""
        try:
            collection = self.db["vector_indexes"]
            docs = collection.find({}, {"document_id": 1, "_id": 0})
            return sorted(
                doc["document_id"]
                for doc in docs
                if doc.get("document_id")
            )
        except Exception as e:
            api_logger.error(f"Error listing vector store documents: {e}")
            return []
    
    def _load_document(self, document_id: str) -> bool:
        """Load document index and metadata from MongoDB"""
        try:
            collection = self.db["vector_indexes"]
            doc = collection.find_one({"document_id": document_id})
            
            if not doc:
                api_logger.warning(f"Index not found in MongoDB for {document_id}")
                return False
            
            # Deserialize index
            index = faiss.deserialize_index(doc["index_data"])
            self._indexes[document_id] = index
            
            # Load metadata
            if "metadata" in doc:
                self._metadata[document_id] = doc["metadata"]
            
            # Load chunks
            if "chunks_data" in doc:
                self._chunks[document_id] = pickle.loads(doc["chunks_data"])
            
            api_logger.info(f"✓ Loaded document from MongoDB: {document_id}")
            return True
        except Exception as e:
            api_logger.error(f"Failed to load document from MongoDB: {e}")
            return False
    
    def get_stats(self, document_id: str) -> dict:
        """Get statistics about a document's index"""
        if document_id not in self._indexes:
            self._load_document(document_id)
        
        if document_id not in self._indexes:
            return {"error": "Document not found"}
        
        index = self._indexes[document_id]
        metadata = self._metadata.get(document_id, [])
        
        return {
            "document_id": document_id,
            "num_vectors": index.ntotal,
            "embedding_dim": self.embedding_dim,
            "num_chunks": len(metadata),
            "total_tokens": sum(len(m.get("content", "").split()) for m in metadata)
        }
