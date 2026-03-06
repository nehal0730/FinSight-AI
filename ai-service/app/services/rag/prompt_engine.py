"""
Prompt Engine - LLM prompting with anti-hallucination mechanisms.

Philosophy:
- Strict system prompts prevent making up information
- Force model to cite sources
- Return "Not found in document" when appropriate
- Include confidence scores in responses
- Structured output for easy parsing

Anti-Hallucination Strategy:
1. System prompt explicitly forbids creativity
2. Context-aware instructions about source documents
3. Confidence scoring based on retrieval confidence
4. Source citation requirement
5. Explicit instruction to reject out-of-context queries
"""

from dataclasses import dataclass
from typing import List, Optional

from app.services.rag.retriever import RetrievedChunk
from app.utils.logging import api_logger


@dataclass
class PromptContext:
    """Context for building prompts."""
    query: str
    retrieved_chunks: List[RetrievedChunk]
    document_name: str = "the document"


class PromptEngine:
    """
    Build LLM prompts with anti-hallucination guardrails.
    
    Key Design:
    - System prompt sets strict boundaries
    - User prompt includes retrieved context
    - Encourage source citations
    - Explicit handling of "not in document" cases
    """
    
    # SYSTEM PROMPT - Sets boundaries for LLM behavior
    SYSTEM_PROMPT = """You are a Financial Intelligence Assistant specialized in analyzing financial documents.

CRITICAL CONSTRAINTS:
1. **Answer ONLY from the provided document context.** Do not use external knowledge.
2. **If the answer is not in the document, respond: "Information not found in document."**
3. **Always cite the source:** Include which section/page the information comes from.
4. **Be precise:** Financial documents require exact figures, not approximations.
5. **No hallucinations:** Never invent data, interpretations, or financial metrics.
6. **Structured output:** Provide clear, bulleted responses for readability.

RESPONSE TEMPLATE:
- **Answer:** [Direct answer from document OR "Information not found in document"]
- **Source:** [Which section/page numbers the answer came from]
- **Confidence:** [HIGH/MEDIUM/LOW] based on information clarity
- **Context:** [Brief explanation if needed]

Remember: Your only source of truth is the provided document context. Reject questions about information not present in the document."""

    # Few-shot examples for better performance
    FINANCIAL_QA_EXAMPLES = """
EXAMPLE 1 - Successful retrieval:
Q: "What was the company's revenue in Q3 2023?"
Relevant context from document: "Q3 2023 Revenue: $42.5 Million"
A: 
- **Answer:** $42.5 Million
- **Source:** Financial Summary section, page 2
- **Confidence:** HIGH
- **Context:** This is explicitly stated in the quarterly results summary.

EXAMPLE 2 - Information not found:
Q: "What is the company's CEO salary?"
Relevant context: [Document discusses revenue, expenses, but no CEO compensation]
A:
- **Answer:** Information not found in document.
- **Source:** No relevant section found
- **Confidence:** N/A
- **Context:** The document does not contain executive compensation details.
"""

    @staticmethod
    def build_system_message() -> str:
        """Get system message with anti-hallucination constraints."""
        return PromptEngine.SYSTEM_PROMPT

    @staticmethod
    def build_user_message(context: PromptContext) -> str:
        """
        Build user message with retrieved context.
        
        Format:
        - Document name for context
        - Retrieved chunks with source info
        - User query
        """
        
        if not context.retrieved_chunks:
            # No context available
            user_msg = f"""Document: {context.document_name}

Query: {context.query}

Context: No relevant information found in the document for this query.

Please respond with: "Information not found in document." """
            return user_msg
        
        # Build context section with retrieved chunks
        context_section = f"Document: {context.document_name}\n\n"
        context_section += "Retrieved Relevant Sections:\n"
        context_section += "=" * 60 + "\n"
        
        for i, retrieved in enumerate(context.retrieved_chunks, 1):
            chunk = retrieved.chunk
            score = retrieved.final_score
            confidence = retrieved.confidence
            
            source_info = f"[Section {i}]"
            if chunk.page_number:
                source_info += f" Page {chunk.page_number}"
            if chunk.section_title:
                source_info += f" | {chunk.section_title}"
            source_info += f" (Relevance: {score:.2f}, Confidence: {confidence:.2f})"
            
            context_section += f"\n{source_info}\n"
            context_section += "-" * 60 + "\n"
            context_section += chunk.content[:500]  # Limit chunk display
            if len(chunk.content) > 500:
                context_section += "... [truncated]"
            context_section += "\n"
        
        context_section += "\n" + "=" * 60 + "\n"
        
        # Build final user message
        user_msg = f"""{context_section}

Query: {context.query}

Instructions:
1. Use ONLY the retrieved sections above to answer.
2. If the answer cannot be found in the retrieved sections, respond with "Information not found in document."
3. Always cite which section (by number above) your answer comes from.
4. Provide confidence level (HIGH/MEDIUM/LOW) for your answer.
5. Use the response template: Answer | Source | Confidence | Context"""
        
        return user_msg
    
    @staticmethod
    def build_messages(context: PromptContext) -> List[dict]:
        """
        Build full message list for LLM API.
        
        Returns:
            List of message dicts: [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        return [
            {
                "role": "system",
                "content": PromptEngine.build_system_message()
            },
            {
                "role": "user",
                "content": PromptEngine.build_user_message(context)
            }
        ]
    
    @staticmethod
    def parse_response(response_text: str) -> dict:
        """
        Parse LLM response into structured format.
        
        Expected format:
        - **Answer:** ...
        - **Source:** ...
        - **Confidence:** ...
        - **Context:** ...
        
        Returns:
            Dict with parsed fields
        """
        result = {
            "answer": "",
            "source": "",
            "confidence": "UNKNOWN",
            "context": "",
            "raw_response": response_text
        }
        
        try:
            # Simple parsing (improve with regex if needed)
            lines = response_text.split('\n')
            
            current_field = None
            current_value = []
            
            for line in lines:
                if "**Answer:**" in line:
                    current_field = "answer"
                    current_value = [line.split("**Answer:**", 1)[1].strip()]
                elif "**Source:**" in line:
                    if current_field:
                        result[current_field] = '\n'.join(current_value).strip()
                    current_field = "source"
                    current_value = [line.split("**Source:**", 1)[1].strip()]
                elif "**Confidence:**" in line:
                    if current_field:
                        result[current_field] = '\n'.join(current_value).strip()
                    current_field = "confidence"
                    current_value = [line.split("**Confidence:**", 1)[1].strip()]
                elif "**Context:**" in line:
                    if current_field:
                        result[current_field] = '\n'.join(current_value).strip()
                    current_field = "context"
                    current_value = [line.split("**Context:**", 1)[1].strip()]
                elif current_field and line.strip():
                    current_value.append(line.strip())
            
            # Store last field
            if current_field:
                result[current_field] = '\n'.join(current_value).strip()
        
        except Exception as e:
            api_logger.error(f"Failed to parse response: {e}")
        
        return result


class ResponseFormatter:
    """Format final responses for API consumers."""
    
    @staticmethod
    def format_rag_response(
        query: str,
        answer: str,
        source: str,
        confidence: str,
        context: str,
        retrieved_chunks: List[RetrievedChunk],
        latency_ms: float
    ) -> dict:
        """
        Format complete RAG response for API.
        
        Includes:
        - Query and answer
        - Source citations with metadata
        - Confidence level
        - Performance metrics
        """
        return {
            "query": query,
            "answer": answer,
            "source": source,
            "confidence": confidence,
            "context": context,
            "citations": [
                {
                    "chunk_id": chunk.chunk.chunk_id,
                    "page": chunk.chunk.page_number,
                    "section": chunk.chunk.section_title,
                    "relevance_score": f"{chunk.final_score:.3f}"
                }
                for chunk in retrieved_chunks
            ],
            "metrics": {
                "chunks_retrieved": len(retrieved_chunks),
                "latency_ms": latency_ms
            }
        }
    
    @staticmethod
    def format_error_response(
        query: str,
        error_message: str,
        error_code: str = "RETRIEVAL_FAILED"
    ) -> dict:
        """Format error response."""
        return {
            "query": query,
            "answer": "Information not found in document.",
            "source": "N/A",
            "confidence": "LOW",
            "context": f"Error: {error_message}",
            "citations": [],
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
