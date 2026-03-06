"""
Document Chunking Module - Recursive chunking with metadata preservation.

Strategy:
1. Split by semantic boundaries (paragraphs, sections)
2. Preserve document structure (maintain headers, context)
3. Track chunk metadata (page number, section, position)
4. Handle overlaps to prevent context loss at boundaries

Philosophy:
- Smart splitting prevents cutting financial statements mid-table
- Metadata enables source citation and traceability
- Overlap ensures no information loss at chunk boundaries
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Chunk:
    """
    A document chunk with rich metadata for traceability.
    
    Attributes:
        content: The actual text content
        chunk_id: Unique identifier (doc_id_chunk_index)
        document_id: Source document ID
        page_number: Source page (if available)
        section_title: Logical section heading
        position: Chunk order in document
        metadata: Additional context (highlighted terms, entities found)
    """
    content: str
    chunk_id: str
    document_id: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    position: int = 0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def word_count(self) -> int:
        return len(self.content.split())
    
    def char_count(self) -> int:
        return len(self.content)
    
    def __repr__(self) -> str: #defines how object prints in logs
        return f"Chunk({self.chunk_id}, page={self.page_number}, words={self.word_count()})"


class DocumentChunker:
    """
    Recursive document chunker with configurable strategy.
    
    Splitting hierarchy:
    1. First, try splitting by section boundaries (headers)
    2. If still too large, split by paragraphs
    3. If still too large, split by sentences
    4. Apply overlap to maintain context
    
    This prevents splitting critical structures like:
    - Financial tables
    - Legal clauses
    - Multi-paragraph concepts
    """
    
    # Patterns for identifying structure
    SECTION_PATTERN = re.compile(r'^(#{1,3}|[A-Z][A-Z\s]+:|\d+\.\s+\w+)$', re.MULTILINE)
    PARAGRAPH_PATTERN = re.compile(r'\n\n+')
    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in tokens (≈4 chars per token)
            chunk_overlap: Overlap between chunks for context preservation
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.char_budget = chunk_size * 4  # Rough: 4 chars per token
        self.overlap_budget = chunk_overlap * 4
    
    def chunk_document(
        self,
        text: str,
        document_id: str,
        page_ranges: Optional[List[tuple]] = None
    ) -> List[Chunk]:
        """
        Chunk a complete document with metadata tracking.
        
        Args:
            text: Full document text
            document_id: Unique document identifier
            page_ranges: Optional list of (page_num, text) tuples for page tracking
        
        Returns:
            List of Chunk objects with metadata
        """
        if not text or not text.strip():
            return []
        
        # Build a position-to-page mapping if provided
        char_pos_to_page = {}
        if page_ranges:
            current_pos = 0
            for page_num, page_text in page_ranges:
                page_end = current_pos + len(page_text)
                # Map character positions to page numbers
                for pos in range(current_pos, page_end):
                    char_pos_to_page[pos] = page_num
                current_pos = page_end
        
        # Perform recursive chunking
        raw_chunks = self._recursive_split(text)
        
        # Apply overlap and create Chunk objects
        chunks = []
        chunk_position = 0
        
        for i, chunk_text in enumerate(raw_chunks):
            if not chunk_text.strip():
                continue
            
            # Determine page number based on chunk position in text
            chunk_pos = text.find(chunk_text)
            if chunk_pos >= 0 and char_pos_to_page:
                page_num = char_pos_to_page.get(chunk_pos)
            else:
                page_num = self._estimate_page(chunk_text, text)
            
            # Extract section title if present
            section_title = self._extract_section_title(chunk_text)
            
            chunk = Chunk(
                content=chunk_text,
                chunk_id=f"{document_id}_chunk_{i:04d}",
                document_id=document_id,
                page_number=page_num,
                section_title=section_title,
                position=chunk_position,
                metadata={
                    "word_count": len(chunk_text.split()),
                    "char_count": len(chunk_text),
                    "chunk_index": i
                }
            )
            chunks.append(chunk)
            chunk_position += 1
        
        return chunks
    
    def _recursive_split(self, text: str) -> List[str]:
        """
        Recursively split text using semantic boundaries.
        
        Returns:
            List of text chunks
        """
        # Start with paragraph splitting (best semantic boundary)
        paragraphs = self.PARAGRAPH_PATTERN.split(text)
        chunks = []
        
        current_chunk = ""
        for para in paragraphs:
            if not para.strip():
                continue
            
            # If adding paragraph exceeds budget, flush current chunk
            if len(current_chunk) + len(para) > self.char_budget:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Handle paragraphs that are still too large
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.char_budget:
                # Split by sentences
                final_chunks.extend(self._split_by_sentences(chunk))
            else:
                final_chunks.append(chunk)
        
        # Apply overlap
        return self._apply_overlap(final_chunks)
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences when paragraphs are still too large."""
        sentences = self.SENTENCE_PATTERN.split(text)
        chunks = []
        current = ""
        
        for sent in sentences:
            if not sent.strip():
                continue
            if len(current) + len(sent) > self.char_budget:
                if current:
                    chunks.append(current)
                current = sent
            else:
                current += " " + sent if current else sent
        
        if current:
            chunks.append(current)
        
        return chunks
    
    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap between chunks to prevent information loss."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                # Add overlap from previous chunk
                prev_chunk = chunks[i - 1]
                
                # Take last N tokens from previous chunk
                overlap_text = self._take_last_n_chars(prev_chunk, self.overlap_budget)
                combined = overlap_text + "\n\n" + chunk
                overlapped.append(combined)
        
        return overlapped
    
    @staticmethod
    def _take_last_n_chars(text: str, n: int) -> str:
        """Take last n characters, respecting word boundaries."""
        if len(text) <= n:
            return text
        
        # Find last complete word within budget
        truncated = text[-n:]
        last_space = truncated.rfind(" ")
        
        if last_space > 0:
            return text[-(n - last_space):]
        return truncated
    
    @staticmethod
    def _estimate_page(chunk_text: str, full_text: str) -> Optional[int]:
        """Estimate page number based on chunk position (rough)."""
        try:
            position = full_text.find(chunk_text)
            if position == -1:
                return None
            
            # Rough estimate: ~3000 chars per page
            return (position // 3000) + 1
        except:
            return None
    
    @staticmethod
    def _extract_section_title(chunk_text: str) -> Optional[str]:
        """Extract section title from chunk if present."""
        lines = chunk_text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line_stripped = line.strip()
            if re.match(r'^(#{1,3}|[A-Z][A-Z\s]+:|^\d+\.)', line_stripped):
                return line_stripped
        return None
