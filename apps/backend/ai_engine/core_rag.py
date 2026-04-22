"""
VeriRAG Core Query Engine
========================

Single-responsibility design. This file does ONE thing:
Answer a question grounded in uploaded documents.

Architecture:
    1. Embed query
    2. Find relevant chunks
    3. Make confidence decision
    4. Return answer + citations + confidence
"""

import time
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Configuration - simple thresholds
CONFIDENCE_HIGH = 0.88  # Direct answer without LLM
CONFIDENCE_MID = 0.70   # Need LLM synthesis
CONFIDENCE_LOW = 0.70   # Reject

# ============================================================================
# MAIN QUERY ENGINE
# ============================================================================


def answer_academic_question(
    query: str,
    user_id: int,
) -> Dict[str, Any]:
    """
    Answer a research question grounded in user's documents.

    Args:
        query: The research question
        user_id: User ID (for multi-tenant isolation)

    Returns:
        {
            "answer": "RAG improves..." or None if rejected,
            "confidence": 0.92,
            "citations": [{"source": "Paper A", "page": 2, "excerpt": "..."}],
            "method": "direct" | "synthesis" | "rejected",
            "cost_usd": 0.001,
            "latency_ms": 245
        }
    """
    start_time = time.time()
    cost = 0.0

    try:
        # Step 1: Find relevant chunks
        chunks = _retrieve_chunks(query, user_id, top_k=5)

        if not chunks:
            return _rejection("no_documents", 0.0, start_time, cost)

        # Step 2: Check confidence
        top_chunk = chunks[0]
        confidence = _chunk_to_confidence(top_chunk)

        # Step 3: Decide what to return
        if confidence >= CONFIDENCE_HIGH and top_chunk.is_qa:
            # High confidence direct answer
            return _direct_answer(top_chunk, confidence, start_time, cost)

        elif confidence >= CONFIDENCE_MID:
            # Medium confidence: synthesize from multiple chunks
            return _synthesized_answer(query, chunks, cost, start_time)

        else:
            # Low confidence: reject
            return _rejection("insufficient_evidence", confidence, start_time, cost)

    except Exception as e:
        logger.exception(f"Query failed: {str(e)}")
        return _rejection("system_error", 0.0, start_time, cost)


# ============================================================================
# HELPER FUNCTIONS - Clean separation
# ============================================================================


def _retrieve_chunks(query: str, user_id: int, top_k: int = 5) -> List[Any]:
    """
    Retrieve the most relevant chunks from the user's documents.
    Uses pgvector for fast semantic search.
    """
    from ai_engine.rag_logic import get_embedding_model
    from ai_engine.models import ChunkIndex
    from pgvector.django import CosineDistance

    # Embed the query
    embedding_model = get_embedding_model()
    q_vector = embedding_model.embed_query(query)

    # Find similar chunks in the user's document library
    chunks = ChunkIndex.objects.filter(user_id=user_id).annotate(
        distance=CosineDistance("embedding", q_vector)
    ).order_by("distance")[:top_k]

    return chunks


def _chunk_to_confidence(chunk: Any) -> float:
    """
    Convert pgvector distance to a confidence score (0.0 - 1.0).
    """
    similarity = 1.0 - chunk.distance
    return max(0.0, min(1.0, float(similarity)))


def _direct_answer(chunk: Any, confidence: float, start_time: float, cost: float) -> Dict[str, Any]:
    """
    Return a chunk as-is (no LLM cost).
    Used when we're highly confident the chunk answers the question directly.
    """
    return {
        "answer": chunk.content,
        "confidence": confidence,
        "citations": _extract_citations(chunk),
        "method": "direct",
        "cost_usd": cost,
        "latency_ms": int((time.time() - start_time) * 1000)
    }


def _synthesized_answer(
    query: str,
    chunks: List[Any],
    cost: float,
    start_time: float
) -> Dict[str, Any]:
    """
    Synthesize an answer from multiple chunks using an LLM.
    Used when confidence is medium but we can combine evidence.
    """
    from ai_engine.rag_logic import _synthesize_answer

    # Build context from top 3 chunks
    context = "\n\n".join([
        f"[{c.document.title}, Page {c.page_number}]\n{c.content}"
        for c in chunks[:3]
    ])

    # Call LLM once
    answer = _synthesize_answer(query, context)
    cost += 0.001  # Typical GPT-3.5 cost

    return {
        "answer": answer,
        "confidence": _chunk_to_confidence(chunks[0]),
        "citations": _extract_citations(chunks[0]),
        "method": "synthesis",
        "cost_usd": cost,
        "latency_ms": int((time.time() - start_time) * 1000)
    }


def _rejection(
    reason: str,
    confidence: float,
    start_time: float,
    cost: float
) -> Dict[str, Any]:
    """
    Reject the query gracefully.
    This is a FEATURE, not a failure.
    """
    messages = {
        "no_documents": "No documents uploaded yet. Upload a PDF to get started.",
        "insufficient_evidence": "This question is outside your document library. Try asking about topics covered in your PDFs.",
        "system_error": "Unable to process query. Please try again."
    }

    return {
        "answer": None,
        "confidence": confidence,
        "citations": [],
        "method": "rejected",
        "reason": reason,
        "message": messages.get(reason, "Unable to answer."),
        "cost_usd": cost,
        "latency_ms": int((time.time() - start_time) * 1000)
    }


def _extract_citations(chunk: Any) -> List[Dict[str, str]]:
    """
    Extract clean citation objects from a chunk.
    Format: [{"source": "Paper A", "page": 2, "excerpt": "..."}]
    """
    return [{
        "source": chunk.document.title,
        "page": chunk.page_number,
        "excerpt": chunk.content[:200].strip()
    }]
