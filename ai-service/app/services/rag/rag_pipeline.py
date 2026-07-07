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
import re
from typing import List, Optional
import numpy as np
import os

from app.config.rag_config import RAGSystemConfig, get_rag_config
from app.services.rag.chunking import DocumentChunker, Chunk
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.mongo_vector_store import MongoVectorStore
from app.services.rag.vector_store import FAISSVectorStore
from app.services.rag.retriever import Retriever, RetrievedChunk
from app.services.rag.prompt_engine import PromptEngine, PromptContext, ResponseFormatter
from app.services.document import TextStore
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
        
        # Initialize vector store - MongoDB or local FAISS
        mongodb_uri = os.getenv("MONGODB_URI")
        if mongodb_uri:
            try:
                self.vector_store = MongoVectorStore(
                    mongo_uri=mongodb_uri,
                    embedding_dim=self.embedding_service.get_embedding_dim()
                )
                api_logger.info("✓ Using MongoDB for vector storage")
            except Exception as e:
                api_logger.error(f"MongoDB initialization failed: {e}. Falling back to local FAISS.")
                self.vector_store = FAISSVectorStore(
                    storage_dir=self.config.vector_store_root,
                    embedding_dim=self.embedding_service.get_embedding_dim()
                )
        else:
            # Use local FAISS for development
            api_logger.info("MONGODB_URI not set. Using local FAISS storage.")
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
            # Verify document exists and self-heal missing indexes from saved text.
            if not self.vector_store.document_exists(document_id):
                saved_text = self._load_saved_text(document_id)
                if saved_text:
                    api_logger.warning(
                        f"Vector index missing for {document_id}; rebuilding from saved extracted text"
                    )
                    reindex_result = self.index_document(
                        text=saved_text,
                        document_id=document_id,
                        page_ranges=None,
                        force_reindex=True,
                    )
                    if reindex_result.get("status") == "error" or not self.vector_store.document_exists(document_id):
                        return ResponseFormatter.format_error_response(
                            query=query,
                            error_message=f"Document {document_id} could not be indexed for retrieval",
                            error_code="DOCUMENT_NOT_FOUND"
                        )
                else:
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
                api_logger.warning(
                    f"No retrieved chunks for {document_id}; attempting full-text fallback"
                )
                full_text = self._load_saved_text(document_id)
                if full_text:
                    latency_ms = (time.time() - start_time) * 1000
                    return self._build_text_fallback_response(
                        query=query,
                        document_id=document_id,
                        full_text=full_text,
                        latency_ms=latency_ms,
                    )

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

            groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not groq_api_key:
                api_logger.warning("GROQ_API_KEY is missing; using extractive fallback response")
                latency_ms = (time.time() - start_time) * 1000
                return self._build_extractive_response(
                    query=query,
                    retrieved=retrieved,
                    document_id=document_id,
                    latency_ms=latency_ms
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

    def _build_extractive_response(
        self,
        query: str,
        retrieved: List[RetrievedChunk],
        document_id: str,
        latency_ms: float
    ) -> dict:
        """Build a document-grounded response without using the external LLM."""
        if not retrieved:
            return ResponseFormatter.format_error_response(
                query=query,
                error_message=f"Document {document_id} indexed, but no relevant sections were found",
                error_code="NO_RESULTS"
            )

        if self._looks_like_transaction_statement(retrieved[0].chunk.content):
            best_chunk = retrieved[0].chunk
            source_parts = ["Section 1"]
            if best_chunk.page_number:
                source_parts.append(f"page {best_chunk.page_number}")
            if best_chunk.section_title:
                source_parts.append(best_chunk.section_title)

            return ResponseFormatter.format_rag_response(
                query=query,
                answer=self._summarize_transaction_text(retrieved[0].chunk.content, query),
                source=" | ".join(source_parts),
                confidence="MEDIUM" if len(retrieved) > 1 else "LOW",
                context=(
                    "Extractive fallback response generated because the external LLM is unavailable. "
                    "The answer is based only on the retrieved document sections shown in the prompt."
                ),
                retrieved_chunks=retrieved,
                latency_ms=latency_ms
            )

        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "what", "are", "there",
            "any", "risk", "factors", "discussed", "about", "your", "document", "please",
            "summarize", "main", "question", "please", "answer", "into", "have", "has",
            "was", "were", "been", "will", "would", "could", "should", "there", "into"
        }

        query_terms = {
            token
            for token in re.findall(r"[A-Za-z0-9]+", query.lower())
            if len(token) > 2 and token not in stopwords
        }

        best_sentence = ""
        best_score = -1.0
        best_chunk = retrieved[0].chunk
        candidate_sentences: list[tuple[float, str]] = []

        for item in retrieved:
            chunk = item.chunk
            sentences = re.split(r"(?<=[.!?])\s+", chunk.content.strip()) or [chunk.content.strip()]
            for sentence in sentences:
                sentence_text = sentence.strip()
                if not sentence_text:
                    continue

                sentence_terms = set(re.findall(r"[A-Za-z0-9]+", sentence_text.lower()))
                overlap = len(query_terms.intersection(sentence_terms))
                if overlap == 0 and any(term in sentence_text.lower() for term in ("risk", "loss", "fraud", "warning", "factor", "issue", "concern")):
                    overlap = 1

                score = overlap + float(item.final_score or 0)
                candidate_sentences.append((score, sentence_text))
                if score > best_score:
                    best_score = score
                    best_sentence = sentence_text
                    best_chunk = chunk

        if candidate_sentences:
            candidate_sentences.sort(key=lambda item: item[0], reverse=True)
            selected_sentences: list[str] = []
            seen_sentences: set[str] = set()
            for _, sentence_text in candidate_sentences:
                normalized = sentence_text.lower()
                if normalized in seen_sentences:
                    continue
                seen_sentences.add(normalized)
                selected_sentences.append(sentence_text)
                if len(selected_sentences) >= 2:
                    break
            best_sentence = " ".join(selected_sentences).strip()

        if not best_sentence:
            best_sentence = retrieved[0].chunk.content.strip().split("\n")[0][:240]

        if len(best_sentence) > 420:
            best_sentence = best_sentence[:417].rstrip() + "..."

        source_parts = ["Section 1"]
        if best_chunk.page_number:
            source_parts.append(f"page {best_chunk.page_number}")
        if best_chunk.section_title:
            source_parts.append(best_chunk.section_title)

        confidence = "LOW"
        if best_score >= 4:
            confidence = "HIGH"
        elif best_score >= 2:
            confidence = "MEDIUM"

        answer = best_sentence
        if not re.search(r"\b(is|are|was|were|has|have|shows|indicates|mentions|states|describes)\b", answer.lower()):
            answer = f"The document says: {best_sentence}"

        context = (
            "Extractive fallback response generated because the external LLM is unavailable. "
            "The answer is based only on the retrieved document sections shown in the prompt."
        )

        return ResponseFormatter.format_rag_response(
            query=query,
            answer=answer,
            source=" | ".join(source_parts),
            confidence=confidence,
            context=context,
            retrieved_chunks=retrieved,
            latency_ms=latency_ms
        )

    def _load_saved_text(self, document_id: str) -> str | None:
        """Load the full cleaned text saved at upload time."""
        try:
            store = TextStore()
            return store.load(document_id)
        except Exception as e:
            api_logger.error(f"Failed to load saved text for {document_id}: {e}")
            return None

    def _build_text_fallback_response(
        self,
        query: str,
        document_id: str,
        full_text: str,
        latency_ms: float,
    ) -> dict:
        """Build a concise response from the saved document text when retrieval returns nothing."""
        if self._looks_like_transaction_statement(full_text):
            return ResponseFormatter.format_rag_response(
                query=query,
                answer=self._summarize_transaction_text(full_text, query),
                source=f"Saved document text fallback for {document_id}",
                confidence="MEDIUM",
                context="Generated from the saved cleaned document text because vector retrieval returned no chunks.",
                retrieved_chunks=[],
                latency_ms=latency_ms,
            )

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", full_text.replace("\n", " "))
            if s.strip()
        ]

        query_lower = query.lower()
        wants_summary = any(word in query_lower for word in ("summarize", "summary", "overview", "main points"))
        wants_risks = any(word in query_lower for word in ("risk", "factor", "factors", "concern", "issue", "red flag"))

        selected_lines: list[str] = []
        keywords = {
            token
            for token in re.findall(r"[A-Za-z0-9]+", query_lower)
            if len(token) > 2
        }

        scored_sentences: list[tuple[int, str]] = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for token in keywords if token in sentence_lower)
            if wants_summary:
                score += 1 if len(sentence.split()) <= 35 else 0
            if wants_risks and any(term in sentence_lower for term in ("risk", "loss", "fraud", "concern", "issue", "warning", "factor")):
                score += 2
            if score > 0:
                scored_sentences.append((score, sentence))

        scored_sentences.sort(key=lambda item: item[0], reverse=True)
        for _, sentence in scored_sentences:
            if sentence not in selected_lines:
                selected_lines.append(sentence)
            if len(selected_lines) >= 3:
                break

        if not selected_lines and wants_summary:
            for paragraph in paragraphs:
                for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                    sentence = sentence.strip()
                    if sentence:
                        selected_lines.append(sentence)
                        break
                if len(selected_lines) >= 2:
                    break

        if not selected_lines:
            selected_lines = sentences[:2] if sentences else [full_text[:240].strip()]

        answer = " ".join(selected_lines).strip()
        if len(answer) > 520:
            answer = answer[:517].rstrip() + "..."

        if wants_summary and answer:
            answer = f"The document appears to discuss: {answer}"

        source = f"Saved document text fallback for {document_id}"
        context = "Generated from the saved cleaned document text because vector retrieval returned no chunks."
        confidence = "MEDIUM" if len(selected_lines) > 1 else "LOW"

        if wants_risks and "risk" not in answer.lower():
            answer = f"The document text was available, but no explicit risk-factor sentence was found. Relevant text: {answer}"

        return ResponseFormatter.format_rag_response(
            query=query,
            answer=answer,
            source=source,
            confidence=confidence,
            context=context,
            retrieved_chunks=[],
            latency_ms=latency_ms,
        )

    @staticmethod
    def _looks_like_transaction_statement(text: str) -> bool:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return False

        header_hits = sum(1 for line in lines[:5] if "date" in line.lower() and "amount" in line.lower())
        dated_rows = sum(1 for line in lines if re.match(r"^\d{4}-\d{2}-\d{2}\s+", line))
        return header_hits > 0 or dated_rows >= 4

    @staticmethod
    def _summarize_transaction_text(text: str, query: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        row_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(Credit|Debit)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$")
        transactions = []

        for line in lines:
            match = row_pattern.match(line)
            if match:
                _, description, txn_type, amount, _balance = match.groups()
                transactions.append((description.strip(), txn_type.lower(), amount))

        if transactions:
            credits = [description for description, txn_type, _amount in transactions if txn_type == "credit"]
            debits = [description for description, txn_type, _amount in transactions if txn_type == "debit"]

            unique_debits = []
            seen = set()
            for description in debits:
                normalized = description.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                unique_debits.append(description)

            summary_bits = ["This is a transaction statement that lists dates, credit and debit entries, balances, and posting locations."]
            if credits:
                summary_bits.append(f"It shows credit activity such as {credits[0]}.")
            if unique_debits:
                summary_bits.append(f"Recurring debit activity includes {', '.join(unique_debits[:6])}.")
            if any(token in query.lower() for token in ("risk", "factor", "concern")):
                summary_bits.append("The statement rows do not explicitly state risk factors or fraud.")

            return " ".join(summary_bits)

        if any(token in query.lower() for token in ("risk", "factor", "concern")):
            return "The document does not explicitly list risk factors in the extracted text."

        first_lines = " ".join(lines[:3])
        if len(first_lines) > 420:
            first_lines = first_lines[:417].rstrip() + "..."
        return first_lines or "Information not found in document."
    
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
