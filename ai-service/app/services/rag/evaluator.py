"""
RAG Evaluator - Test and validate retrieval quality.

Philosophy:
- Define test cases manually (ground truth queries + expected results)
- Measure retrieval precision, relevance, and latency
- Identify failure cases
- No hallucination detection (LLM evaluation)

Metrics:
- MRR (Mean Reciprocal Rank): Position of first relevant result
- NDCG (Normalized Discounted Cumulative Gain): Ranking quality
- P@k: Precision at k results
- Retrieval latency: Time to retrieve top-k chunks
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict

from app.services.rag.rag_pipeline import RAGPipeline
from app.config.rag_config import RAGSystemConfig, RAGConfigPresets
from app.utils.logging import api_logger


@dataclass
class TestCase:
    """Single evaluation test case."""
    query: str
    expected_keywords: List[str]  # Keywords that should appear in retrieved chunks
    document_id: str
    name: str = ""
    category: str = ""  # e.g., "risk", "financial", "compliance"


@dataclass
class RetrievalResult:
    """Result of retrieval for a test case."""
    query: str
    retrieved_chunks: int
    relevant_chunks: int  # How many chunks contained expected keywords
    mrr: float  # Mean Reciprocal Rank
    ndcg: float  # Normalized Discounted Cumulative Gain
    p_at_5: float  # Precision @ 5
    latency_ms: float
    success: bool


class RAGEvaluator:
    """
    Evaluate RAG system on predefined test cases.
    
    Workflow:
        evaluator = RAGEvaluator(pipeline)
        results = evaluator.evaluate(test_cases)
        report = evaluator.generate_report(results)
    """
    
    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.results: List[RetrievalResult] = []
    
    def evaluate(self, test_cases: List[TestCase]) -> List[RetrievalResult]:
        """
        Run evaluation on test cases.
        
        Args:
            test_cases: List of TestCase objects
        
        Returns:
            List of RetrievalResult objects with metrics
        """
        api_logger.info(f"Starting evaluation: {len(test_cases)} test cases")
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            api_logger.info(f"Test {i}/{len(test_cases)}: {test_case.query[:60]}")
            
            result = self._evaluate_single(test_case)
            results.append(result)
            
            # Log intermediate result
            api_logger.info(
                f"  Result: {result.relevant_chunks}/{result.retrieved_chunks} relevant, "
                f"MRR={result.mrr:.3f}, NDCG={result.ndcg:.3f}, "
                f"P@5={result.p_at_5:.3f}, latency={result.latency_ms:.0f}ms"
            )
        
        self.results = results
        return results
    
    def _evaluate_single(self, test_case: TestCase) -> RetrievalResult:
        """Evaluate a single test case."""
        start_time = time.time()
        
        try:
            # Retrieve
            retrieved = self.pipeline.retriever.retrieve(
                query=test_case.query,
                document_id=test_case.document_id,
                top_k=10  # Evaluate top-10 for detailed metrics
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if not retrieved:
                return RetrievalResult(
                    query=test_case.query,
                    retrieved_chunks=0,
                    relevant_chunks=0,
                    mrr=0.0,
                    ndcg=0.0,
                    p_at_5=0.0,
                    latency_ms=latency_ms,
                    success=False
                )
            
            # Compute relevance
            relevance_scores = self._compute_relevance(
                retrieved,
                test_case.expected_keywords
            )
            
            # Compute metrics
            mrr = self._compute_mrr(relevance_scores)
            ndcg = self._compute_ndcg(relevance_scores)
            p_at_5 = self._compute_p_at_k(relevance_scores, k=5)
            relevant_count = sum(relevance_scores)
            
            return RetrievalResult(
                query=test_case.query,
                retrieved_chunks=len(retrieved),
                relevant_chunks=relevant_count,
                mrr=mrr,
                ndcg=ndcg,
                p_at_5=p_at_5,
                latency_ms=latency_ms,
                success=relevant_count > 0
            )
        
        except Exception as e:
            api_logger.error(f"Test failed: {e}")
            return RetrievalResult(
                query=test_case.query,
                retrieved_chunks=0,
                relevant_chunks=0,
                mrr=0.0,
                ndcg=0.0,
                p_at_5=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                success=False
            )
    
    @staticmethod
    def _compute_relevance(retrieved, expected_keywords: List[str]) -> List[int]:
        """
        Compute binary relevance for each retrieved chunk.
        
        Returns:
            List of 0/1 indicating relevance
        """
        relevance = []
        for retrieved_chunk in retrieved:
            content_lower = retrieved_chunk.chunk.content.lower()
            is_relevant = any(
                keyword.lower() in content_lower
                for keyword in expected_keywords
            )
            relevance.append(1 if is_relevant else 0)
        return relevance
    
    @staticmethod
    def _compute_mrr(relevance: List[int]) -> float:
        """
        Mean Reciprocal Rank: position of first relevant result.
        
        Returns:
            MRR score (0-1, higher is better)
        """
        for i, rel in enumerate(relevance):
            if rel == 1:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def _compute_ndcg(relevance: List[int], ideal_length: int = 5) -> float:
        """
        Normalized Discounted Cumulative Gain.
        
        Returns:
            NDCG score (0-1, higher is better)
        """
        # DCG: discount by log(position)
        dcg = sum(
            rel / (1 + i) ** 0.5  # Discount by sqrt(position)
            for i, rel in enumerate(relevance[:ideal_length])
        )
        
        # Ideal DCG: all relevant
        ideal_dcg = sum(
            1.0 / (1 + i) ** 0.5
            for i in range(min(len(relevance), ideal_length))
        )
        
        if ideal_dcg == 0:
            return 0.0
        
        return dcg / ideal_dcg
    
    @staticmethod
    def _compute_p_at_k(relevance: List[int], k: int = 5) -> float:
        """
        Precision @ K: fraction of top-k results that are relevant.
        
        Returns:
            Precision score (0-1, higher is better)
        """
        if not relevance:
            return 0.0
        
        top_k = relevance[:k]
        return sum(top_k) / len(top_k)
    
    def generate_report(self) -> dict:
        """Generate evaluation report with aggregate metrics."""
        if not self.results:
            return {"status": "no_results"}
        
        # Aggregate metrics
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        success_rate = successful / total_tests if total_tests > 0 else 0
        
        mrr_scores = [r.mrr for r in self.results]
        ndcg_scores = [r.ndcg for r in self.results]
        p_at_5_scores = [r.p_at_5 for r in self.results]
        latencies = [r.latency_ms for r in self.results]
        
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0
        avg_p_at_5 = sum(p_at_5_scores) / len(p_at_5_scores) if p_at_5_scores else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful": successful,
                "success_rate": success_rate
            },
            "metrics": {
                "mean_reciprocal_rank": avg_mrr,
                "mean_ndcg": avg_ndcg,
                "mean_precision_at_5": avg_p_at_5,
                "mean_latency_ms": avg_latency
            },
            "detailed_results": [asdict(r) for r in self.results]
        }
    
    def save_report(self, report: dict, output_path: Path):
        """Save evaluation report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        api_logger.info(f"Evaluation report saved: {output_path}")


# ========== PREDEFINED TEST CASES ==========

def get_sample_test_cases() -> List[TestCase]:
    # """Sample test cases for Driver Feedback and Sentiment Dashboard RAG."""
    # Legacy financial test cases kept for quick rollback/reference:
    return [
        TestCase(
            name="Revenue Query",
            query="What was the total revenue for the last quarter?",
            expected_keywords=["revenue", "quarter", "million", "billion"],
            category="financial",
            document_id="sample_doc"
        ),
        TestCase(
            name="Risk Assessment",
            query="What are the main business risks?",
            expected_keywords=["risk", "exposure", "threat", "danger"],
            category="risk",
            document_id="sample_doc"
        ),
        TestCase(
            name="Compliance",
            query="Are there any compliance violations?",
            expected_keywords=["compliance", "violation", "regulation", "requirement"],
            category="compliance",
            document_id="sample_doc"
        ),
        TestCase(
            name="Cash Flow",
            query="What is the company's cash flow situation?",
            expected_keywords=["cash", "flow", "liquidity", "payment"],
            category="financial",
            document_id="sample_doc"
        ),
    # return [
    #     TestCase(
    #         name="Supported Entities",
    #         query="Which entity types are listed in the multi-entity feedback support section?",
    #         expected_keywords=["Driver", "Trip", "Mobile App", "Marshal"],
    #         category="configuration",
    #         document_id="sample_doc"
    #     ),
    #     TestCase(
    #         name="Feature Flag Behavior",
    #         query="What should happen in the form when feedback sections are disabled through feature flags?",
    #         expected_keywords=["Disabled sections", "must NOT appear", "No feedback options available", "page reload"],
    #         category="form_ux",
    #         document_id="sample_doc"
    #     ),
    #     TestCase(
    #         name="Overview Panel Metrics",
    #         query="What does the dashboard overview panel need to show for sentiment analytics?",
    #         expected_keywords=["today / 7 days / 30 days", "Positive / Neutral / Negative", "Average sentiment score", "alert threshold"],
    #         category="analytics",
    #         document_id="sample_doc"
    #     ),
    #     TestCase(
    #         name="Leaderboard and Alerts",
    #         query="What are the required leaderboard color thresholds and alert notification behaviors?",
    #         expected_keywords=["green (≥ 4.0)", "amber (2.5–3.9)", "red (< 2.5)", "bell icon", "unread count badge"],
    #         category="dashboard",
    #         document_id="sample_doc"
    #     ),
    ]
