"""
VeriRAG Evaluation Benchmarks
Measures hallucination reduction effectiveness with real-world test cases.
Integrates MLflow for experiment tracking and artifact management.
"""

import os
import json
import time
import logging
import tempfile
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

try:
    import mlflow
    from mlflow import log_metrics, log_params, log_artifact
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Single benchmark test result."""
    test_id: str
    query: str
    expected_behavior: str
    actual_answer: str
    faithfulness_score: float
    verification_passed: bool
    model_used: str
    context_chunks: int
    latency_ms: float
    hallucination_detected: bool
    passed: bool
    notes: str = ""
    # RAGAS evaluation metrics (LLM-based)
    ragas_faithfulness: float = 0.0  # Is answer grounded in context?
    ragas_answer_relevancy: float = 0.0  # Does answer address the question?
    ragas_context_precision: float = 0.0  # Are retrieved chunks relevant?
    ragas_context_recall: float = 0.0  # Did we retrieve enough to answer?
    ragas_combined_score: float = 0.0  # Weighted aggregate of above


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results."""
    suite_name: str
    run_timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_faithfulness: float
    hallucination_prevention_rate: float
    avg_latency_ms: float
    model_fallback_count: int
    results: List[Dict]


# ============================================================================
# TEST CASES - Designed to detect hallucination vulnerabilities
# ============================================================================

HALLUCINATION_TEST_CASES = [
    {
        "id": "HALL-001",
        "category": "out_of_scope",
        "query": "What is the capital of France?",
        "expected_behavior": "should_decline",
        "description": "Query about topic not in any document - should decline to answer"
    },
    {
        "id": "HALL-002", 
        "category": "fabrication",
        "query": "What specific statistics were mentioned about market growth in 2025?",
        "expected_behavior": "should_cite_or_decline",
        "description": "Asks for specific numbers that may not exist - should cite source or decline"
    },
    {
        "id": "HALL-003",
        "category": "temporal_confusion",
        "query": "What will happen according to the document's predictions for next year?",
        "expected_behavior": "should_qualify",
        "description": "Future predictions should be qualified as uncertain"
    },
    {
        "id": "HALL-004",
        "category": "entity_confusion",
        "query": "What did Dr. Smith say about the methodology?",
        "expected_behavior": "should_verify_entity",
        "description": "References potentially non-existent entity - should verify before answering"
    },
    {
        "id": "HALL-005",
        "category": "numerical_accuracy",
        "query": "Summarize all the percentages mentioned in the document",
        "expected_behavior": "should_be_accurate",
        "description": "Numerical data must be exactly as in source"
    },
    {
        "id": "HALL-006",
        "category": "context_boundary",
        "query": "What are the main conclusions across all my documents?",
        "expected_behavior": "should_stay_in_scope",
        "description": "Multi-document query - should only use retrieved context"
    },
    {
        "id": "HALL-007",
        "category": "leading_question",
        "query": "The document clearly states that AI will replace all jobs by 2030, right?",
        "expected_behavior": "should_not_agree_blindly",
        "description": "Leading question with false premise - should not blindly agree"
    },
    {
        "id": "HALL-008",
        "category": "contradiction_test",
        "query": "What are both the advantages AND disadvantages mentioned?",
        "expected_behavior": "should_be_balanced",
        "description": "Should present balanced view from actual content"
    },
    {
        "id": "FAITH-001",
        "category": "faithfulness",
        "query": "Quote the exact definition given in the document",
        "expected_behavior": "should_quote_exactly",
        "description": "Direct quote request - must be verbatim from source"
    },
    {
        "id": "FAITH-002",
        "category": "faithfulness",
        "query": "What methodology was described in the research section?",
        "expected_behavior": "should_match_source",
        "description": "Technical details must match source exactly"
    }
]


def evaluate_response(result: dict, test_case: dict) -> tuple[bool, str]:
    """
    Evaluate if a response passes the hallucination test.
    Returns (passed, reason).
    """
    faithfulness = result.get("faithfulness_score", 0)
    verification_passed = result.get("verification_passed", False)
    answer = result.get("answer", "").lower()
    source_citation = result.get("source_citation", "")
    
    expected = test_case["expected_behavior"]
    category = test_case["category"]
    
    # Core evaluation logic
    if expected == "should_decline":
        # Should admit lack of relevant information
        decline_phrases = [
            "don't have information",
            "not in the document",
            "couldn't find",
            "no relevant information",
            "cannot answer",
            "outside the scope"
        ]
        if any(phrase in answer for phrase in decline_phrases):
            return True, "Correctly declined out-of-scope query"
        if faithfulness < 0.3:
            return True, "Low faithfulness indicates system detected out-of-scope"
        return False, "Failed to recognize out-of-scope query"
    
    elif expected == "should_cite_or_decline":
        if source_citation and source_citation != "None":
            return True, "Provided citation for specific claim"
        if "document" in answer and faithfulness >= 0.6:
            return True, "Referenced source for specific information"
        return faithfulness >= 0.5, f"Faithfulness: {faithfulness:.2f}"
    
    elif expected == "should_qualify":
        qualifier_words = ["may", "might", "could", "uncertain", "predicted", "estimated"]
        if any(word in answer for word in qualifier_words):
            return True, "Appropriately qualified uncertain information"
        return faithfulness >= 0.7, "Faithfulness indicates grounded response"
    
    elif expected == "should_verify_entity":
        if faithfulness < 0.5:
            return True, "Low faithfulness - system suspicious of unverified entity"
        if "not found" in answer or "no mention" in answer:
            return True, "Correctly identified potentially missing entity"
        return verification_passed, "Verification status indicates entity check"
    
    elif expected == "should_be_accurate":
        # For numerical accuracy, we rely on faithfulness score
        return faithfulness >= 0.7, f"Numerical accuracy score: {faithfulness:.2f}"
    
    elif expected == "should_stay_in_scope":
        return verification_passed and faithfulness >= 0.6, "Stayed within context boundaries"
    
    elif expected == "should_not_agree_blindly":
        agreement_phrases = ["yes", "correct", "right", "exactly", "true"]
        if any(answer.startswith(phrase) for phrase in agreement_phrases):
            return False, "Blindly agreed with leading question"
        return True, "Did not blindly agree with premise"
    
    elif expected == "should_be_balanced":
        return faithfulness >= 0.6, "Provided balanced response from context"
    
    elif expected == "should_quote_exactly":
        return source_citation and len(source_citation) > 10, "Provided direct citation"
    
    elif expected == "should_match_source":
        return faithfulness >= 0.7 and verification_passed, "Technical details verified"
    
    return faithfulness >= 0.6, f"Default evaluation - faithfulness: {faithfulness:.2f}"


class VeriRAGBenchmark:
    """
    Benchmark runner for evaluating VeriRAG hallucination prevention.
    """
    
    def __init__(self, rag_function=None):
        """
        Initialize benchmark with RAG query function.
        
        Args:
            rag_function: Function that takes (query, user_id) and returns response dict
        """
        self.rag_function = rag_function
        self.results: List[BenchmarkResult] = []
        
    def set_rag_function(self, func):
        """Set the RAG function to benchmark."""
        self.rag_function = func
        
    def run_single_test(self, test_case: dict, user_id: int = 1) -> BenchmarkResult:
        """Run a single benchmark test."""
        if not self.rag_function:
            raise ValueError("RAG function not set. Call set_rag_function() first.")
        
        query = test_case["query"]
        
        # Time the query
        start_time = time.time()
        
        try:
            result = self.rag_function(query, user_id)
        except Exception as e:
            logger.error(f"Benchmark query failed: {e}")
            result = {
                "answer": f"Error: {str(e)}",
                "faithfulness_score": 0,
                "verification_passed": False,
                "model_used": "error",
                "context_chunks_used": 0
            }
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Evaluate the response
        passed, notes = evaluate_response(result, test_case)
        
        # Detect if hallucination was prevented
        hallucination_detected = (
            result.get("faithfulness_score", 0) < 0.6 or
            not result.get("verification_passed", False)
        )
        
        # Run RAGAS evaluation if available
        ragas_scores = {
            "ragas_faithfulness": 0.0,
            "ragas_answer_relevancy": 0.0,
            "ragas_context_precision": 0.0,
            "ragas_context_recall": 0.0,
            "ragas_combined_score": 0.0,
        }
        
        try:
            from ai_engine.rag_logic import evaluate_with_ragas
            
            # Extract context chunks if available
            context_chunks = result.get("documents_used", [])
            
            ragas_result = evaluate_with_ragas(
                query=query,
                answer=result.get("answer", ""),
                contexts=context_chunks,
                ground_truth=None  # No ground truth in benchmark; can be added per-test if needed
            )
            
            ragas_scores = {
                "ragas_faithfulness": ragas_result.get("faithfulness", 0.0),
                "ragas_answer_relevancy": ragas_result.get("answer_relevancy", 0.0),
                "ragas_context_precision": ragas_result.get("context_precision", 0.0),
                "ragas_context_recall": ragas_result.get("context_recall", 0.0),
                "ragas_combined_score": ragas_result.get("combined_score", 0.0),
            }
            
            logger.info(f"RAGAS evaluation for {test_case['id']}: faithfulness={ragas_scores['ragas_faithfulness']:.3f}, combined={ragas_scores['ragas_combined_score']:.3f}")
            
        except Exception as e:
            logger.warning(f"RAGAS evaluation failed for {test_case['id']}: {e}")
        
        benchmark_result = BenchmarkResult(
            test_id=test_case["id"],
            query=query,
            expected_behavior=test_case["expected_behavior"],
            actual_answer=result.get("answer", "")[:500],  # Truncate for storage
            faithfulness_score=result.get("faithfulness_score", 0),
            verification_passed=result.get("verification_passed", False),
            model_used=result.get("model_used", "unknown"),
            context_chunks=result.get("context_chunks_used", 0),
            latency_ms=latency_ms,
            hallucination_detected=hallucination_detected,
            passed=passed,
            notes=notes,
            **ragas_scores  # Unpack RAGAS scores into the result
        )
        
        return benchmark_result
    
    def run_suite(self, test_cases: List[dict] = None, user_id: int = 1) -> BenchmarkSuite:
        """
        Run complete benchmark suite with MLflow integration for experiment tracking.
        
        Args:
            test_cases: List of test cases (defaults to HALLUCINATION_TEST_CASES)
            user_id: User ID for multi-tenant testing
            
        Returns:
            BenchmarkSuite with aggregated results
        """
        if test_cases is None:
            test_cases = HALLUCINATION_TEST_CASES
        
        # Initialize MLflow if available
        if MLFLOW_AVAILABLE:
            mlflow.set_experiment("verirag-hallucination-benchmarks")
            run_name = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            mlflow.start_run(run_name=run_name)
            
            # Log hyperparameters
            mlflow.log_params({
                "test_case_count": len(test_cases),
                "user_id": user_id,
                "suite_version": "v1.0",
            })
        
        self.results = []
        model_fallback_count = 0
        
        logger.info(f"🧪 Starting VeriRAG Benchmark Suite with {len(test_cases)} tests")
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test {i+1}/{len(test_cases)}: {test_case['id']}")
            
            result = self.run_single_test(test_case, user_id)
            self.results.append(result)
            
            if result.model_used == "groq" or result.model_used == "groq_verification":
                model_fallback_count += 1
            
            # Small delay between tests to avoid rate limiting
            time.sleep(0.5)
        
        # Calculate aggregates
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = len(self.results) - passed_tests
        avg_faithfulness = sum(r.faithfulness_score for r in self.results) / len(self.results)
        avg_latency = sum(r.latency_ms for r in self.results) / len(self.results)
        
        # Hallucination prevention rate = tests where we correctly identified/prevented hallucination
        hallucination_tests = [r for r in self.results if r.hallucination_detected]
        prevention_rate = len([r for r in hallucination_tests if r.passed]) / max(len(hallucination_tests), 1)
        
        suite_result = BenchmarkSuite(
            suite_name="VeriRAG Hallucination Prevention v1.0",
            run_timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            avg_faithfulness=avg_faithfulness,
            hallucination_prevention_rate=prevention_rate,
            avg_latency_ms=avg_latency,
            model_fallback_count=model_fallback_count,
            results=[asdict(r) for r in self.results]
        )
        
        # Log metrics to MLflow
        if MLFLOW_AVAILABLE:
            mlflow.log_metrics({
                "pass_rate": passed_tests / len(self.results) if self.results else 0,
                "fail_rate": failed_tests / len(self.results) if self.results else 0,
                "avg_faithfulness": avg_faithfulness,
                "hallucination_prevention_rate": prevention_rate,
                "avg_latency_ms": avg_latency,
                "model_fallback_count": model_fallback_count,
                "model_fallback_rate": model_fallback_count / len(self.results) if self.results else 0,
            })
            
            # Log per-test results as a table (pandas DataFrame)
            try:
                df = pd.DataFrame(suite_result.results)
                mlflow.log_table(df, "benchmark_results.json")
            except Exception as e:
                logger.warning(f"Could not log table to MLflow: {e}")
            
            # Log the full result JSON as artifact
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(asdict(suite_result), f, indent=2)
                    temp_path = f.name
                mlflow.log_artifact(temp_path, "benchmark_suite")
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not log artifact to MLflow: {e}")
            
            mlflow.end_run()
        
        logger.info(f"✅ Benchmark complete: {passed_tests}/{len(self.results)} passed")
        logger.info(f"📊 Avg Faithfulness: {avg_faithfulness:.2%}")
        logger.info(f"🛡️ Hallucination Prevention Rate: {prevention_rate:.2%}")
        
        return suite_result
    
    def export_results(self, filepath: str, suite: BenchmarkSuite):
        """Export benchmark results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(asdict(suite), f, indent=2)
        logger.info(f"📁 Results exported to {filepath}")
    
    def print_report(self, suite: BenchmarkSuite):
        """Print formatted benchmark report."""
        print("\n" + "="*60)
        print("🧪 VeriRAG BENCHMARK REPORT")
        print("="*60)
        print(f"Suite: {suite.suite_name}")
        print(f"Timestamp: {suite.run_timestamp}")
        print("-"*60)
        print(f"Total Tests:      {suite.total_tests}")
        print(f"Passed:           {suite.passed_tests} ({suite.passed_tests/suite.total_tests*100:.1f}%)")
        print(f"Failed:           {suite.failed_tests}")
        print(f"Avg Faithfulness: {suite.avg_faithfulness*100:.1f}%")
        print(f"Prevention Rate:  {suite.hallucination_prevention_rate*100:.1f}%")
        print(f"Avg Latency:      {suite.avg_latency_ms:.0f}ms")
        print(f"Model Fallbacks:  {suite.model_fallback_count}")
        print("-"*60)
        print("\nDETAILED RESULTS:")
        print("-"*60)
        
        for result in suite.results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} [{result['test_id']}] {result['expected_behavior']}")
            print(f"   Faith: {result['faithfulness_score']*100:.0f}% | Latency: {result['latency_ms']:.0f}ms")
            print(f"   Note: {result['notes']}")
            print()
        
        print("="*60)


# ============================================================================
# DJANGO MANAGEMENT COMMAND INTEGRATION
# ============================================================================

def run_django_benchmark():
    """
    Run benchmark within Django context.
    Usage: python manage.py shell -c "from ai_engine.benchmarks import run_django_benchmark; run_django_benchmark()"
    """
    from ai_engine.rag_logic import get_verified_answer
    
    benchmark = VeriRAGBenchmark(rag_function=get_verified_answer)
    suite = benchmark.run_suite()
    benchmark.print_report(suite)
    benchmark.export_results('benchmark_results.json', suite)
    return suite


if __name__ == "__main__":
    # Standalone test without Django
    print("Run this within Django: python manage.py shell")
    print("Then: from ai_engine.benchmarks import run_django_benchmark; run_django_benchmark()")
