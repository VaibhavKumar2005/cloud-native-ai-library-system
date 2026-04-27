"""
Faithfulness Scorer Module - Hallucination Detection via Semantic Verification & RAGAS
This is the core differentiator for VeriRAG: dual-layer verification prevents hallucinations.

Two verification strategies:
1. Semantic: Fast cosine similarity between answer and context embeddings
2. RAGAS: LLM-based evaluation using domain-specific metrics
"""

import os
import logging
import re
from prometheus_client import Histogram

# Import utilities
from ai_engine.vector_store import get_embedding_model

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & METRICS
# ============================================================================
FAITHFULNESS_THRESHOLD = float(os.environ.get("FAITHFULNESS_THRESHOLD", "0.6"))
"""Score below 0.6 triggers rejection (hallucination detected)"""

# Prometheus metrics
FAITHFULNESS_HISTOGRAM = Histogram(
    'verirag_faithfulness_score',
    'Distribution of faithfulness scores (0-1)',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Import tracing utilities (graceful fallback)
try:
    from ai_engine.tracing import (
        trace_context,
        add_span_attributes,
    )
except ImportError:
    # Fallback no-op implementations
    from contextlib import nullcontext
    def trace_context(*args, **kwargs):
        return nullcontext()
    def add_span_attributes(*args, **kwargs):
        pass


def verify_faithfulness(answer: str, context: str, query: str) -> tuple:
    """
    Semantic faithfulness verification using embedding cosine similarity.
    Fast, reliable baseline that detects subtle hallucinations.
    
    Args:
        answer (str): Generated response to verify
        context (str): Retrieved context from documents
        query (str): Original user query (for tracing)
        
    Returns:
        tuple: (score: float [0-1], explanation: str)
            score: Confidence that answer is grounded in context
            explanation: Human-readable verification result
            
    Example:
        >>> score, explanation = verify_faithfulness(
        ...     "RAG uses vector embeddings",
        ...     "RAG systems employ embeddings and similarity search",
        ...     "What is RAG?"
        ... )
        >>> score > 0.7
        True
    """
    with trace_context(
        "rag.verification.semantic",
        {
            "rag.query.length": len(query or ""),
            "rag.answer.length": len(answer or ""),
            "rag.context.length": len(context or ""),
        },
    ):
        if not answer or not context:
            add_span_attributes({"rag.verification.score": 0.5})
            return 0.5, "Answer or context is empty"
        
        try:
            # Get embeddings for answer and context using the same model
            embedding_model = get_embedding_model()
            answer_embedding = embedding_model.embed_query(answer)
            context_embedding = embedding_model.embed_query(context)
            
            # Compute cosine similarity between answer and context embeddings
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            similarity_matrix = cosine_similarity(
                [answer_embedding], 
                [context_embedding]
            )
            similarity_score = float(similarity_matrix[0][0])
            
            # Normalize to 0-1 range
            final_score = max(0.0, min(1.0, similarity_score))
            
            add_span_attributes(
                {
                    "rag.verification.score": round(final_score, 4),
                    "rag.verification.method": "semantic_cosine_similarity",
                }
            )
            explanation = f"Semantic similarity: {final_score:.2%}"
            return final_score, explanation
            
        except Exception as e:
            logger.error(f"Semantic verification failed, falling back to heuristic: {e}")
            # Fallback to simple word overlap if embeddings fail
            return _verify_faithfulness_heuristic(answer, context, query)


def _verify_faithfulness_heuristic(answer: str, context: str, query: str) -> tuple:
    """
    Fallback word-overlap heuristic when embeddings fail.
    Used when Azure OpenAI embeddings are unavailable.
    
    Args:
        answer (str): Generated response
        context (str): Retrieved context
        query (str): Original query
        
    Returns:
        tuple: (score: float, explanation: str)
    """
    answer_lower = answer.lower()
    context_lower = context.lower()
    
    # Extract 4+ letter words
    answer_words = set(re.findall(r'\b\w{4,}\b', answer_lower))
    context_words = set(re.findall(r'\b\w{4,}\b', context_lower))
    
    if not answer_words:
        return 0.5, "Unable to extract key terms from answer"
    
    # Calculate overlap and novelty
    overlap = answer_words.intersection(context_words)
    coverage = len(overlap) / len(answer_words) if answer_words else 0
    new_terms = answer_words - context_words
    novelty_penalty = min(len(new_terms) * 0.05, 0.3)
    base_score = coverage - novelty_penalty
    final_score = max(0.0, min(1.0, base_score + 0.3))
    
    add_span_attributes({"rag.verification.score": final_score})
    return final_score, f"Word overlap: {len(overlap)}/{len(answer_words)} terms found in context"


def evaluate_with_ragas(query: str, answer: str, contexts: list, ground_truth: str = None) -> dict:
    """
    LLM-based evaluation using RAGAS framework.
    Comprehensive evaluation using four dimensions:
    
    - faithfulness: Is answer grounded in context? (critical - 50% weight)
    - answer_relevancy: Does answer address the question? (30% weight)
    - context_precision: Are retrieved chunks relevant? (20% weight)
    - context_recall: Did we retrieve enough? (requires ground_truth)
    
    Args:
        query (str): Original user question
        answer (str): Generated response
        contexts (list): Retrieved document chunks (Document objects or strings)
        ground_truth (str, optional): Expected answer for recall calculation
        
    Returns:
        dict: Scores in range [0.0, 1.0]
        {
            "faithfulness": 0.85,
            "answer_relevancy": 0.90,
            "context_precision": 0.88,
            "context_recall": 0.0,
            "combined_score": 0.86  # Weighted aggregate
        }
        
    Raises:
        Falls back gracefully to verify_faithfulness() if RAGAS unavailable
        
    Example:
        >>> scores = evaluate_with_ragas(
        ...     query="What is RAG?",
        ...     answer="RAG uses embeddings and vector search",
        ...     contexts=[doc1, doc2, doc3],
        ...     ground_truth="RAG retrieves context for LLM generation"
        ... )
        >>> scores["combined_score"] >= 0.6
        True
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
        
        # Prepare data in RAGAS format
        # contexts should be list of text strings from retrieved documents
        if isinstance(contexts, list) and len(contexts) > 0:
            if hasattr(contexts[0], 'page_content'):
                # LangChain Document objects
                context_texts = [doc.page_content for doc in contexts]
            else:
                # Plain strings
                context_texts = contexts
        else:
            context_texts = []
        
        data_dict = {
            "question": [query],
            "answer": [answer],
            "contexts": [context_texts],
        }
        
        # Include ground truth if provided for context recall calculation
        metrics_to_evaluate = [faithfulness, answer_relevancy, context_precision]
        if ground_truth:
            data_dict["ground_truth"] = [ground_truth]
            metrics_to_evaluate.append(context_recall)
        
        # Create RAGAS dataset and evaluate
        dataset = Dataset.from_dict(data_dict)
        result = evaluate(dataset, metrics=metrics_to_evaluate)
        
        # Extract scores with safe defaults
        ragas_scores = {
            "faithfulness": round(float(result.get("faithfulness", 0.5)), 3),
            "answer_relevancy": round(float(result.get("answer_relevancy", 0.5)), 3),
            "context_precision": round(float(result.get("context_precision", 0.5)), 3),
            "context_recall": round(float(result.get("context_recall", 0.0)), 3) if ground_truth else 0.0,
        }
        
        # Calculate weighted combined score
        # Faithfulness: 50% (most critical - must be grounded)
        # Answer relevancy: 30% (must address the question)
        # Context precision: 20% (retrieval quality matters)
        ragas_scores["combined_score"] = round(
            (ragas_scores["faithfulness"] * 0.5) +
            (ragas_scores["answer_relevancy"] * 0.3) +
            (ragas_scores["context_precision"] * 0.2),
            3
        )
        
        # Log metrics to Prometheus
        FAITHFULNESS_HISTOGRAM.observe(ragas_scores["faithfulness"])
        
        # Attach all scores to trace span
        add_span_attributes({
            "rag.ragas.faithfulness": ragas_scores["faithfulness"],
            "rag.ragas.answer_relevancy": ragas_scores["answer_relevancy"],
            "rag.ragas.context_precision": ragas_scores["context_precision"],
            "rag.ragas.context_recall": ragas_scores["context_recall"],
            "rag.ragas.combined_score": ragas_scores["combined_score"],
        })
        
        logger.info(f"RAGAS evaluation complete - faithfulness: {ragas_scores['faithfulness']:.2f}")
        return ragas_scores
        
    except ImportError as e:
        logger.warning(f"RAGAS not available ({e}), falling back to semantic verification")
        # Fallback: use semantic verification
        score, explanation = verify_faithfulness(answer, "\n".join(
            [c.page_content if hasattr(c, 'page_content') else str(c) for c in contexts]
        ), query)
        return {
            "faithfulness": score,
            "answer_relevancy": 0.5,
            "context_precision": 0.5,
            "context_recall": 0.0,
            "combined_score": score,
        }
    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        # Safe fallback
        return {
            "faithfulness": 0.5,
            "answer_relevancy": 0.5,
            "context_precision": 0.5,
            "context_recall": 0.0,
            "combined_score": 0.5,
        }


def score_answer(query: str, answer: str, contexts: list, use_ragas: bool = True) -> dict:
    """
    Main entry point for faithfulness scoring.
    Orchestrates both semantic and RAGAS verification.
    
    Args:
        query (str): Original user question
        answer (str): Generated response
        contexts (list): Retrieved document chunks
        use_ragas (bool): Try RAGAS evaluation first (slower but more accurate)
        
    Returns:
        dict: {
            "query": str,
            "answer": str,
            "score": float,  # Combined score
            "semantic_score": float,  # Fast baseline
            "ragas_scores": dict or None,  # Full RAGAS eval if available
            "passed_verification": bool,  # score >= FAITHFULNESS_THRESHOLD
            "explanation": str,
        }
    """
    context_text = "\n".join(
        [c.page_content if hasattr(c, 'page_content') else str(c) for c in contexts]
    ) if contexts else ""
    
    # Always run semantic verification (fast baseline)
    semantic_score, semantic_explanation = verify_faithfulness(answer, context_text, query)
    
    ragas_scores = None
    combined_score = semantic_score
    
    # Try RAGAS evaluation if requested
    if use_ragas:
        try:
            ragas_scores = evaluate_with_ragas(query, answer, contexts)
            combined_score = ragas_scores["combined_score"]
        except Exception as e:
            logger.warning(f"RAGAS evaluation failed, using semantic score: {e}")
    
    passed_verification = combined_score >= FAITHFULNESS_THRESHOLD
    
    return {
        "query": query,
        "answer": answer,
        "score": combined_score,
        "semantic_score": semantic_score,
        "ragas_scores": ragas_scores,
        "passed_verification": passed_verification,
        "threshold": FAITHFULNESS_THRESHOLD,
        "explanation": semantic_explanation if not ragas_scores else f"RAGAS combined: {combined_score:.2%}",
    }
