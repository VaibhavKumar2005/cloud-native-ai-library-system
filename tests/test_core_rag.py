"""
Test suite for core RAG pipeline
Tests the three-tier confidence system and basic query flow
"""

import pytest
from unittest.mock import patch, MagicMock
from ai_engine.core_rag import (
    answer_academic_question,
    _chunk_to_confidence,
    _direct_answer,
    _rejection,
)


class TestAcademicRAG:
    """Test the main query pipeline"""

    @patch('ai_engine.core_rag._retrieve_chunks')
    def test_query_with_no_documents(self, mock_retrieve):
        """Should reject gracefully when no documents are uploaded"""
        mock_retrieve.return_value = []

        result = answer_academic_question(
            query="What is RAG?",
            user_id=1
        )

        assert result['method'] == 'rejected'
        assert result['answer'] is None
        assert result['reason'] == 'no_documents'
        assert 'No documents uploaded' in result['message']

    @patch('ai_engine.core_rag._retrieve_chunks')
    def test_query_high_confidence_direct_answer(self, mock_retrieve):
        """Should return chunk directly when confidence >= 0.88"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 0.05  # High similarity
        mock_chunk.is_qa = True
        mock_chunk.content = "RAG improves accuracy by grounding responses..."
        mock_chunk.document.title = "Smith et al. (2020)"
        mock_chunk.page_number = 2
        mock_chunk.document.metadata = {}

        mock_retrieve.return_value = [mock_chunk]

        with patch('ai_engine.core_rag._extract_citations', return_value=[]):
            result = answer_academic_question(
                query="What is RAG?",
                user_id=1
            )

        assert result['method'] == 'direct'
        assert result['answer'] is not None
        assert result['confidence'] >= 0.88

    @patch('ai_engine.core_rag._retrieve_chunks')
    def test_query_low_confidence_rejection(self, mock_retrieve):
        """Should reject when confidence < 0.70"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 1.2  # Low similarity (far apart)
        mock_chunk.is_qa = False

        mock_retrieve.return_value = [mock_chunk]

        result = answer_academic_question(
            query="Some obscure topic",
            user_id=1
        )

        assert result['method'] == 'rejected'
        assert result['answer'] is None
        assert result['confidence'] < 0.70

    @patch('ai_engine.core_rag._retrieve_chunks')
    @patch('ai_engine.core_rag._synthesized_answer')
    def test_query_medium_confidence_synthesis(self, mock_synth, mock_retrieve):
        """Should synthesize with LLM when confidence is 0.70-0.88"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 0.25  # Medium similarity
        mock_chunk.is_qa = False
        mock_chunk.document.title = "Paper A"
        mock_chunk.page_number = 1

        mock_retrieve.return_value = [mock_chunk]

        with patch('ai_engine.core_rag._extract_citations', return_value=[]):
            result = answer_academic_question(
                query="Compare X and Y",
                user_id=1
            )

        # Should attempt synthesis
        assert result['method'] in ['synthesis', 'rejected']


class TestConfidenceScoring:
    """Test confidence score calculation"""

    def test_chunk_to_confidence_high(self):
        """Distance 0.05 should equal high confidence"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 0.05
        confidence = _chunk_to_confidence(mock_chunk)
        assert confidence >= 0.95

    def test_chunk_to_confidence_medium(self):
        """Distance 0.25 should equal medium confidence"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 0.25
        confidence = _chunk_to_confidence(mock_chunk)
        assert 0.70 <= confidence <= 0.80

    def test_chunk_to_confidence_low(self):
        """Distance 1.5 should equal low confidence"""
        mock_chunk = MagicMock()
        mock_chunk.distance = 1.5
        confidence = _chunk_to_confidence(mock_chunk)
        assert confidence <= 0.50


class TestResponseFormats:
    """Test response structure and formats"""

    def test_direct_answer_structure(self):
        """Direct answer should have all required fields"""
        mock_chunk = MagicMock()
        mock_chunk.content = "Test answer"
        mock_chunk.distance = 0.1

        with patch('ai_engine.core_rag._extract_citations', return_value=[]):
            result = _direct_answer(
                chunk=mock_chunk,
                confidence=0.92,
                start_time=0,
                cost=0.0
            )

        assert 'answer' in result
        assert 'confidence' in result
        assert 'method' in result
        assert 'citations' in result
        assert 'latency_ms' in result
        assert 'cost_usd' in result

    def test_rejection_structure(self):
        """Rejection should have helpful message"""
        result = _rejection(
            reason='insufficient_evidence',
            confidence=0.5,
            start_time=0,
            cost=0.0
        )

        assert result['method'] == 'rejected'
        assert result['answer'] is None
        assert 'message' in result
        assert result['message'] != ""


class TestIntegration:
    """Integration tests (requires real Django models)"""

    @pytest.mark.django_db
    def test_end_to_end_query_no_documents(self):
        """Full flow: user with no documents should get rejection"""
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        result = answer_academic_question(
            query="Test question",
            user_id=user.id
        )

        assert result['method'] == 'rejected'
        assert result['answer'] is None


if __name__ == '__main__':
    pytest.main([__file__])
