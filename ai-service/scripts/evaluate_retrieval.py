#!/usr/bin/env python3
"""
Retrieval Evaluation Script - Test RAG retrieval quality on sample documents.

Usage:
    python scripts/evaluate_retrieval.py --document-id "sample_doc"
    python scripts/evaluate_retrieval.py --preset high_precision
    python scripts/evaluate_retrieval.py --preset fast_inference --save-report
"""

import sys
import json
import argparse
from pathlib import Path

# Ensure we can import from the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag.rag_pipeline import RAGPipeline
from app.services.rag.evaluator import RAGEvaluator, TestCase, get_sample_test_cases
from app.config.rag_config import RAGConfigPresets, get_rag_config, set_rag_config
from app.utils.logging import api_logger


def create_sample_document(pipeline: RAGPipeline, doc_id: str = "sample_doc") -> bool:
    """
    Create a sample document for testing (financial document excerpt).
    
    Returns:
        True if successful
    """
    # Sample financial document text
    sample_text = """
    FINANCIAL SUMMARY - Q3 2023 Report
    
    Revenue and Earnings:
    The company achieved total revenue of $156.2 million in Q3 2023, representing a 12% 
    increase compared to Q3 2022. Net profit increased to $28.5 million, an improvement 
    of 18% year-over-year. Earnings per share (EPS) reached $2.45, up from $2.10 in the 
    prior year quarter.
    
    Cash Flow Analysis:
    Operating cash flow for the nine-month period ended September 30, 2023 was $67.8 million, 
    compared to $52.3 million in the same period of 2022. Free cash flow (operating cash flow 
    minus capital expenditures) was $45.2 million. The company maintains strong liquidity 
    with $89.7 million in cash and cash equivalents.
    
    Business Risk Assessment:
    The company faces several key business risks:
    1. Market volatility: Exposure to foreign exchange risk due to 35% international revenue
    2. Regulatory exposure: Compliance requirements in 12 jurisdictions, with potential fines up to $5M
    3. Operational risk: Dependence on 3 major suppliers for 60% of production
    4. Technology risk: Legacy system replacement project running 15% over budget
    
    Debt and Capital Structure:
    Total debt increased slightly to $125.3 million from $118.7 million, primarily due to 
    acquisition financing. The debt-to-equity ratio stands at 0.65, within target range of 0.5-0.8. 
    Interest coverage ratio of 4.2x indicates healthy debt servicing capability.
    
    Compliance and Regulatory Status:
    The company is in full compliance with all regulatory requirements. No violations were 
    reported during the nine-month period. We completed our SOX 404 audit with no material 
    weaknesses identified. Environmental compliance certifications are current.
    """
    
    page_ranges = [
        (1, sample_text[:len(sample_text)//2]),
        (2, sample_text[len(sample_text)//2:])
    ]
    
    result = pipeline.index_document(
        text=sample_text,
        document_id=doc_id,
        page_ranges=page_ranges
    )
    
    success = result.get("status") == "success"
    
    if success:
        print(f"\n✓ Sample document indexed: {doc_id}")
        print(f"  - Chunks: {result.get('chunks_created', 0)}")
        print(f"  - Total words: {result.get('total_words', 0)}")
        print(f"  - Indexing time: {result.get('indexing_time_sec', 0):.2f}s")
    else:
        print(f"\n✗ Failed to index sample document: {result.get('error')}")
    
    return success


def run_evaluation(
    document_id: str = "sample_doc",
    preset: str = "production",
    test_cases: list = None
) -> dict:
    """
    Run RAG evaluation.
    
    Args:
        document_id: Document to evaluate against
        preset: Configuration preset (production, high_precision, fast_inference)
        test_cases: Custom test cases (uses defaults if None)
    
    Returns:
        Evaluation report dictionary
    """
    # Select configuration
    config_map = {
        "production": RAGConfigPresets.production(),
        "high_precision": RAGConfigPresets.high_precision(),
        "fast_inference": RAGConfigPresets.fast_inference(),
        "evaluation": RAGConfigPresets.evaluation(),
    }
    
    if preset not in config_map:
        print(f"Unknown preset: {preset}. Using production.")
        preset = "production"
    
    config = config_map[preset]
    set_rag_config(config)
    
    print(f"\n📋 Evaluation Configuration: {preset}")
    print(f"  - Chunk size: {config.chunking.chunk_size}")
    print(f"  - Embedding model: {config.embedding.model.value}")
    print(f"  - Top-k: {config.retrieval.top_k}")
    print(f"  - Similarity threshold: {config.retrieval.similarity_threshold}")
    print(f"  - Re-ranking: {config.retrieval.rerank_enabled}")
    
    # Initialize pipeline
    pipeline = RAGPipeline(config)
    
    # Use provided test cases or defaults
    if test_cases is None:
        test_cases = get_sample_test_cases()
    
    # Update document IDs
    for tc in test_cases:
        tc.document_id = document_id
    
    # Run evaluation
    evaluator = RAGEvaluator(pipeline)
    results = evaluator.evaluate(test_cases)
    
    # Generate report
    report = evaluator.generate_report()
    
    return report, test_cases


def print_report(report: dict, test_cases: list):
    """Pretty-print evaluation report."""
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print("="*70)
    
    summary = report.get("summary", {})
    metrics = report.get("metrics", {})
    
    print(f"\nSummary:")
    print(f"  Total tests: {summary.get('total_tests', 0)}")
    print(f"  Successful: {summary.get('successful', 0)}")
    print(f"  Success rate: {summary.get('success_rate', 0):.1%}")
    
    print(f"\nRetrieval Metrics:")
    print(f"  Mean Reciprocal Rank (MRR): {metrics.get('mean_reciprocal_rank', 0):.3f}")
    print(f"  Mean NDCG: {metrics.get('mean_ndcg', 0):.3f}")
    print(f"  Mean Precision @ 5: {metrics.get('mean_precision_at_5', 0):.3f}")
    print(f"  Mean Latency: {metrics.get('mean_latency_ms', 0):.1f} ms")
    
    print(f"\nDetailed Results:")
    print("-" * 70)
    
    for result, test_case in zip(report.get("detailed_results", []), test_cases):
        print(f"\nTest: {test_case.name}")
        print(f"Query: {test_case.query}")
        print(f"  ✓ Relevant: {result['relevant_chunks']}/{result['retrieved_chunks']}")
        print(f"  • MRR: {result['mrr']:.3f}")
        print(f"  • NDCG: {result['ndcg']:.3f}")
        print(f"  • P@5: {result['p_at_5']:.3f}")
        print(f"  • Latency: {result['latency_ms']:.1f} ms")
        print(f"  • Success: {'✓' if result['success'] else '✗'}")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval quality"
    )
    parser.add_argument(
        "--document-id",
        default="Driver_Feedback_&_Sentiment_Dashboard_20260305193046_109b1118",
        help="Document ID to evaluate against"
    )
    parser.add_argument(
        "--preset",
        default="production",
        choices=["production", "high_precision", "fast_inference", "evaluation"],
        help="Configuration preset"
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create sample document before evaluation"
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save report to JSON file"
    )
    
    args = parser.parse_args()
    
    print("\n🚀 FinSight RAG Evaluation")
    print("=" * 70)
    
    # Create sample document if requested
    if args.create_sample:
        pipeline = RAGPipeline()
        if not create_sample_document(pipeline, args.document_id):
            print("Failed to create sample document")
            return 1
    
    # Run evaluation
    try:
        report, test_cases = run_evaluation(
            document_id=args.document_id,
            preset=args.preset
        )
        
        print_report(report, test_cases)
        
        # Save report if requested
        if args.save_report:
            report_path = Path(__file__).parent.parent / "evaluation_report.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Report saved: {report_path}")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        api_logger.error(f"Evaluation error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
