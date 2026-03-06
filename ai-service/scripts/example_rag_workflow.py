#!/usr/bin/env python3
"""
Example: End-to-End RAG Workflow

This script demonstrates how to:
1. Index a document
2. Query the document
3. Handle responses

Run with: python scripts/example_rag_workflow.py
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Check if Groq API key is loaded
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key or not groq_key.startswith("gsk_"):
    print(f"  WARNING: GROQ_API_KEY not set or invalid")
    print(f"   Expected format: gsk_xxxxxxx...")
    print(f"   Loaded: {groq_key[:20] if groq_key else 'NOT SET'}...")
    print(f"   .env path: {env_path}")
    if not env_path.exists():
        print(f"   ❌ File does not exist. Creating template...")
else:
    print(f"✓ GROQ_API_KEY loaded successfully ({groq_key[:10]}...)")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RAG components
from app.config.rag_config import RAGConfigPresets, set_rag_config
from app.services.rag.rag_pipeline import RAGPipeline


def main():
    print("\n" + "="*70)
    print("FinSight RAG System - Example Workflow")
    print("="*70)
    
    # ========== STEP 1: Configure ==========
    print("\n 1️ CONFIGURATION")
    print("-" * 70)
    
    # Use production preset
    config = RAGConfigPresets.production()
    set_rag_config(config)
    
    print(f"✓ Using preset: PRODUCTION")
    print(f"  - Chunk size: {config.chunking.chunk_size} tokens")
    print(f"  - Embedding model: {config.embedding.model.value}")
    print(f"  - Top-k: {config.retrieval.top_k}")
    print(f"  - Similarity threshold: {config.retrieval.similarity_threshold}")
    
    # ========== STEP 2: Create Pipeline ==========
    print("\n 2️ INITIALIZE PIPELINE")
    print("-" * 70)
    
    pipeline = RAGPipeline(config)
    print("✓ RAG Pipeline initialized")
    
    # ========== STEP 3: Index Document ==========
    print("\n3️⃣ INDEX DOCUMENT")
    print("-" * 70)
    
    # Sample financial document
    sample_document = """
    QUARTERLY FINANCIAL REPORT - Q3 2023
    
    EXECUTIVE SUMMARY
    The company achieved record revenues of $287.5 million in Q3 2023, 
    representing a 23% increase year-over-year. Net income grew to $38.2 million,
    with a healthy net margin of 13.3%.
    
    FINANCIAL RESULTS
    Key metrics:
    - Revenue: $287.5M (+23% YoY)
    - Operating Income: $45.3M (+18% YoY)
    - Net Income: $38.2M (+26% YoY)
    - Earnings Per Share: $1.92 (+25% YoY)
    
    BUSINESS OPERATIONS
    The company operates in three main segments:
    1. North America: $142.3M revenue (49% of total)
    2. Europe: $89.6M revenue (31% of total)
    3. Asia Pacific: $55.6M revenue (20% of total)
    
    RISK ANALYSIS
    Key risks identified in our business:
    - Foreign exchange volatility: International sales are 51% of revenue
    - Supply chain disruption: Concentrated in Southeast Asia (32% of suppliers)
    - Technology transition risk: Legacy system migration ongoing
    - Regulatory changes: New compliance requirements in EU and UK
    
    CASH FLOW POSITION
    Strong cash generation:
    - Operating Cash Flow: $52.3M (nine-month YTD)
    - Free Cash Flow: $38.7M after capex
    - Cash Balance: $156.2M
    - Debt: $125.0M
    - Net Debt Ratio: 0.43x (healthy level)
    
    OUTLOOK & GUIDANCE
    For Q4 2023, we expect:
    - Revenue: $295-310M
    - Operating margin: 15.5-16.0%
    - Full year 2023 EPS: $7.20-7.35
    
    CONCLUSION
    Strong operational execution and market demand support continued growth.
    The company is well-positioned for successful transition to next fiscal year.
    """
    
    doc_id = "example_financial_report_q3_2023"
    
    print(f"Indexing document: {doc_id}")
    print(f"Document size: {len(sample_document)} characters")
    
    result = pipeline.index_document(
        text=sample_document,
        document_id=doc_id,
        force_reindex=True  # Force re-index even if already exists
    )
    
    if "error" in result:
        if "already indexed" in str(result.get("error", "")).lower():
            print(f"Document already indexed (skipping re-index)")
        else:
            print(f"Indexing failed: {result['error']}")
            return 1
    elif result.get("status") == "success":
        print(f" Document indexed successfully")
        print(f"  - Chunks created: {result.get('chunks_created', 'N/A')}")
        print(f"  - Total words: {result.get('total_words', 'N/A')}")
        print(f"  - Embedding dimension: {result.get('embedding_dim', 'N/A')}")
        print(f"  - Indexing time: {result.get('indexing_time_sec', 0):.2f}s")
    else:
        print(f" Document processed ({result})")
    
    # ========== STEP 4: Run Queries ==========
    print("\n 4️ RUN QUERIES")
    print("-" * 70)
    
    test_queries = [
        "What was the company's revenue in Q3 2023?",
        "What are the main business risks?",
        "What is the company's cash position?",
        "How much debt does the company have?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        print("-" * 50)
        
        response = pipeline.query(
            query=query,
            document_id=doc_id
        )
        
        if "error" in response:
            print(f"✗ Error: {response['error']['message']}")
            continue
        
        print(f"Answer: {response['answer'][:200]}...")
        print(f"Source: {response['source']}")
        print(f"Confidence: {response['confidence']}")
        print(f"Latency: {response['metrics']['latency_ms']:.0f}ms")
        print(f"Chunks retrieved: {response['metrics']['chunks_retrieved']}")
    
    # ========== STEP 5: Document Statistics ==========
    print("\n 5️ DOCUMENT STATISTICS")
    print("-" * 70)
    
    stats = pipeline.get_document_stats(doc_id)
    print(f"Document: {stats['document_id']}")
    print(f"  Chunks: {stats['chunk_count']}")
    print(f"  Total characters: {stats['total_characters']}")
    print(f"  Total words: {stats['total_words']}")
    print(f"  Average chunk size: {stats['avg_chunk_size']:.0f} chars")
    
    # ========== STEP 6: List Documents ==========
    print("\n 6️ LIST INDEXED DOCUMENTS")
    print("-" * 70)
    
    documents = pipeline.list_documents()
    print(f"Indexed documents: {len(documents)}")
    for doc in documents:
        print(f"  - {doc}")
    
    # ========== STEP 7: Delete Document ==========
    print("\n 7️ CLEANUP")
    print("-" * 70)
    
    # pipeline.delete_document(doc_id)
    # print(f"✓ Document {doc_id} deleted")
    
    print(f"✓ Skipped deletion (document still indexed for further testing)")
    
    # ========== Summary ==========
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE!")
    print("="*70)
    
    print("\nNext steps:")
    print("1. Test with your actual financial documents")
    print("2. Evaluate retrieval quality: python scripts/evaluate_retrieval.py")
    print("3. Integrate with frontend: Call /query endpoint")
    print("4. Monitor production metrics: Latency, accuracy, hallucinations")
    print("5. Fine-tune configuration based on evaluation results")
    
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
