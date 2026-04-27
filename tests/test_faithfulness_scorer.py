"""
Tests for Faithfulness Scorer - Hallucination Detection Module
Tests the core verification logic used in the demo.

Test scenarios:
1. Semantic verification (fast baseline)
2. RAGAS evaluation (comprehensive)
3. Score aggregation and thresholding
4. Demo queries: Q1 (valid), Q2 (valid), Q3 (rejection)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_engine.faithfulness_scorer import (
    verify_faithfulness,
    evaluate_with_ragas,
    score_answer,
    FAITHFULNESS_THRESHOLD,
)


class TestSemanticVerification:
    """Test basic semantic faithfulness verification"""
    
    @patch('ai_engine.faithfulness_scorer.get_embedding_model')
    def test_high_semantic_similarity(self, mock_embedding):
        """Answer grounded in context → high score"""
        # Mock the embedding model to return similar vectors
        mock_model = MagicMock()
        mock_model.embed_query.side_effect = [
            [0.9, 0.1, 0.0],  # answer embedding
            [0.88, 0.12, 0.0],  # context embedding (similar)
        ]
        mock_embedding.return_value = mock_model
        
        answer = "Machine learning models are trained on data"
        context = "Machine learning trains models using datasets"
        query = "What is machine learning?"
        
        score, explanation = verify_faithfulness(answer, context, query)
        
        assert 0.0 <= score <= 1.0, "Score must be in range [0, 1]"
        assert score > 0.5, "High similarity should yield score > 0.5"
        assert "similarity" in explanation.lower(), "Explanation should mention method"
    
    @patch('ai_engine.faithfulness_scorer.get_embedding_model')
    def test_low_semantic_similarity(self, mock_embedding):
        """Answer contradicts context → low score"""
        # Mock with opposite/dissimilar vectors
        mock_model = MagicMock()
        mock_model.embed_query.side_effect = [
            [1.0, 0.0, 0.0],  # answer embedding
            [0.0, 1.0, 0.0],  # context embedding (opposite)
        ]
        mock_embedding.return_value = mock_model
        
        answer = "The Earth is flat and stationary"
        context = "The Earth is a spherical planet orbiting the Sun"
        query = "What shape is the Earth?"
        
        score, explanation = verify_faithfulness(answer, context, query)
        
        assert 0.0 <= score <= 1.0
        assert score < 0.5, "Contradictory answer should yield low score"
    
    def test_empty_answer_or_context(self):
        """Graceful handling of empty inputs"""
        # Empty answer
        score, explanation = verify_faithfulness("", "Some context", "Query?")
        assert score == 0.5, "Empty answer should return neutral score"
        
        # Empty context
        score, explanation = verify_faithfulness("Some answer", "", "Query?")
        assert score == 0.5, "Empty context should return neutral score"
        
        # Both empty
        score, explanation = verify_faithfulness("", "", "Query?")
        assert score == 0.5, "Both empty should return neutral score"
    
    @patch('ai_engine.faithfulness_scorer.get_embedding_model')
    def test_identical_answer_and_context(self, mock_embedding):
        """Perfect match → highest score"""
        # Mock with identical vectors
        mock_model = MagicMock()
        mock_model.embed_query.side_effect = [
            [1.0, 0.0, 0.0],  # answer embedding
            [1.0, 0.0, 0.0],  # context embedding (identical)
        ]
        mock_embedding.return_value = mock_model
        
        text = "RAG systems use vector embeddings for semantic search"
        
        score, explanation = verify_faithfulness(text, text, "Tell me about RAG")
        
        assert score > 0.9, "Identical text should score near 1.0"


class TestRAGASEvaluation:
    """Test RAGAS-based comprehensive evaluation"""
    
    @patch('ragas.evaluate')
    def test_ragas_high_quality(self, mock_evaluate):
        """High-quality answer → all metrics pass"""
        mock_evaluate.return_value = {
            "faithfulness": 0.95,
            "answer_relevancy": 0.92,
            "context_precision": 0.88,
        }
        
        scores = evaluate_with_ragas(
            query="What is RAG?",
            answer="RAG retrieves context for LLM generation",
            contexts=["RAG uses retrievers and LLMs"]
        )
        
        assert scores["faithfulness"] == 0.95
        assert scores["answer_relevancy"] == 0.92
        assert scores["context_precision"] == 0.88
        assert scores["combined_score"] == pytest.approx(
            0.95*0.5 + 0.92*0.3 + 0.88*0.2, rel=0.01
        )
    
    @patch('ragas.evaluate')
    def test_ragas_low_faithfulness(self, mock_evaluate):
        """Hallucination detected → low faithfulness"""
        mock_evaluate.return_value = {
            "faithfulness": 0.3,  # LOW - hallucination
            "answer_relevancy": 0.85,
            "context_precision": 0.80,
        }
        
        scores = evaluate_with_ragas(
            query="What is RAG?",
            answer="RAG uses quantum computing for embeddings",  # Hallucinated detail
            contexts=["RAG uses neural networks for embeddings"]
        )
        
        assert scores["faithfulness"] == 0.3
        assert scores["combined_score"] < 0.6, "Should fail threshold with low faithfulness"
    
    def test_ragas_unavailable_fallback(self):
        """If RAGAS library missing → fall back to semantic"""
        with patch('ragas.evaluate', side_effect=ImportError("RAGAS not installed")):
            scores = evaluate_with_ragas(
                query="What is RAG?",
                answer="RAG uses retrieval and generation",
                contexts=["RAG systems retrieve and generate"]
            )
            
            # Should still return valid scores
            assert "faithfulness" in scores
            assert "combined_score" in scores
            assert scores["faithfulness"] > 0, "Fallback should provide a score"
    
    def test_ragas_with_ground_truth(self):
        """With ground truth → include context_recall metric"""
        with patch('ragas.evaluate') as mock_eval:
            mock_eval.return_value = {
                "faithfulness": 0.85,
                "answer_relevancy": 0.90,
                "context_precision": 0.88,
                "context_recall": 0.92,
            }
            
            scores = evaluate_with_ragas(
                query="What is RAG?",
                answer="RAG uses retrieval",
                contexts=["RAG retrieves context"],
                ground_truth="RAG is Retrieval-Augmented Generation"
            )
            
            assert scores["context_recall"] == 0.92, "Should evaluate recall with ground truth"


class TestScoreAggregation:
    """Test score aggregation and thresholding"""
    
    def test_weighted_scoring(self):
        """Combined score uses correct weights: 50% faithfulness, 30% relevancy, 20% precision"""
        with patch('ragas.evaluate') as mock_eval:
            mock_eval.return_value = {
                "faithfulness": 1.0,    # 100% - full weight = 0.5
                "answer_relevancy": 0.0,  # 0% - no weight
                "context_precision": 0.0,  # 0% - no weight
            }
            
            scores = evaluate_with_ragas(
                query="Q",
                answer="A",
                contexts=["C"]
            )
            
            # Combined should be: 1.0*0.5 + 0.0*0.3 + 0.0*0.2 = 0.5
            assert scores["combined_score"] == 0.5
    
    def test_threshold_boundary(self):
        """Boundary testing around FAITHFULNESS_THRESHOLD"""
        with patch('ragas.evaluate') as mock_eval:
            # Just below threshold
            mock_eval.return_value = {
                "faithfulness": 0.55,
                "answer_relevancy": 0.55,
                "context_precision": 0.55,
            }
            
            result = score_answer(
                query="Q",
                answer="A",
                contexts=["C"]
            )
            
            assert result["passed_verification"] == False, "Score below threshold should fail"
            
            # Just above threshold
            mock_eval.return_value = {
                "faithfulness": 0.65,
                "answer_relevancy": 0.65,
                "context_precision": 0.65,
            }
            
            result = score_answer(
                query="Q",
                answer="A",
                contexts=["C"]
            )
            
            assert result["passed_verification"] == True, "Score above threshold should pass"


class TestDemoQueries:
    """Test the three demo queries: Q1 (valid), Q2 (valid), Q3 (rejection)"""
    
    @patch('ragas.evaluate')
    def test_demo_query_1_valid(self, mock_eval):
        """Query 1: Valid in-domain question → should ACCEPT"""
        mock_eval.return_value = {
            "faithfulness": 0.88,
            "answer_relevancy": 0.92,
            "context_precision": 0.85,
        }
        
        result = score_answer(
            query="How does RAG reduce hallucination?",
            answer="RAG grounds responses in retrieved context, reducing factual errors by preventing the model from generating unsupported claims.",
            contexts=[
                "RAG systems retrieve relevant documents and use them as context for generation",
                "By providing ground truth documents, RAG reduces hallucination",
            ]
        )
        
        assert result["passed_verification"] == True, "Valid Q1 should pass verification"
        assert result["score"] >= 0.6, "Valid answer should score >= threshold"
        print(f"✅ Q1 PASSED - Score: {result['score']:.2f}")
    
    @patch('ragas.evaluate')
    def test_demo_query_2_valid(self, mock_eval):
        """Query 2: Valid in-domain question → should ACCEPT"""
        mock_eval.return_value = {
            "faithfulness": 0.91,
            "answer_relevancy": 0.89,
            "context_precision": 0.87,
        }
        
        result = score_answer(
            query="What is a vector database?",
            answer="A vector database stores high-dimensional embeddings and enables semantic similarity search, critical for RAG systems.",
            contexts=[
                "Vector databases like pgvector store embeddings",
                "Similarity search in vector databases powers semantic retrieval",
            ]
        )
        
        assert result["passed_verification"] == True, "Valid Q2 should pass verification"
        assert result["score"] >= 0.6, "Valid answer should score >= threshold"
        print(f"✅ Q2 PASSED - Score: {result['score']:.2f}")
    
    @patch('ragas.evaluate')
    def test_demo_query_3_rejection(self, mock_eval):
        """Query 3: Out-of-domain question → should REJECT (hallucination detected)"""
        mock_eval.return_value = {
            "faithfulness": 0.25,  # LOW - not grounded in context
            "answer_relevancy": 0.40,  # Doesn't match question
            "context_precision": 0.20,  # Context not relevant
        }
        
        result = score_answer(
            query="What is GraphRAG?",  # Out of scope - no documents about GraphRAG
            answer="GraphRAG uses multi-level graph structures for hierarchical retrieval.",  # Hallucinated detail
            contexts=[
                "This document discusses standard RAG, not GraphRAG",
                "RAG typically uses flat vector stores",
            ]
        )
        
        assert result["passed_verification"] == False, "Invalid Q3 should REJECT (hallucination detected)"
        assert result["score"] < 0.6, "Out-of-domain answer should score < threshold"
        print(f"🛑 Q3 REJECTED - Score: {result['score']:.2f} (hallucination detected)")


class TestScoreAnswerOrchestration:
    """Test the main score_answer() orchestration function"""
    
    def test_semantic_baseline_used_when_ragas_unavailable(self):
        """With use_ragas=False → use only semantic verification"""
        result = score_answer(
            query="What is RAG?",
            answer="RAG uses retrieval and generation",
            contexts=["RAG retrieves and generates"],
            use_ragas=False
        )
        
        assert result["ragas_scores"] is None, "Should not use RAGAS"
        assert result["semantic_score"] > 0, "Should have semantic score"
        assert result["score"] == result["semantic_score"], "Score should be semantic score"
    
    @patch('ragas.evaluate')
    def test_ragas_override_when_available(self, mock_eval):
        """With use_ragas=True → prefer RAGAS scores"""
        mock_eval.return_value = {
            "faithfulness": 0.95,
            "answer_relevancy": 0.90,
            "context_precision": 0.88,
        }
        
        result = score_answer(
            query="What is RAG?",
            answer="RAG uses retrieval and generation",
            contexts=["RAG retrieves and generates"],
            use_ragas=True
        )
        
        assert result["ragas_scores"] is not None, "Should use RAGAS when available"
        assert result["score"] != result["semantic_score"], "Score should prefer RAGAS"
    
    def test_result_structure(self):
        """Result should contain all required fields"""
        result = score_answer(
            query="Q",
            answer="A",
            contexts=["C"],
            use_ragas=False
        )
        
        required_fields = [
            "query", "answer", "score", "semantic_score", "ragas_scores",
            "passed_verification", "threshold", "explanation"
        ]
        
        for field in required_fields:
            assert field in result, f"Result missing required field: {field}"


class TestThresholdConfiguration:
    """Test threshold configuration and behavior"""
    
    def test_threshold_value(self):
        """Verify default threshold is 0.6"""
        assert FAITHFULNESS_THRESHOLD == 0.6, "Default threshold should be 0.6"
    
    def test_threshold_in_result(self):
        """Threshold value should be included in result"""
        result = score_answer(
            query="Q",
            answer="A",
            contexts=["C"],
            use_ragas=False
        )
        
        assert result["threshold"] == FAITHFULNESS_THRESHOLD
        assert result["threshold"] == 0.6


if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v", "-s"])
