"""
VeriRAG MCP Server - Model Context Protocol Server
Exposes VeriRAG RAG and document management capabilities to Claude Desktop and other MCP clients.

Usage:
  1. Install fastmcp: pip install fastmcp
  2. Add to Claude Desktop config (~/.config/Claude/claude_desktop_config.json on Mac/Linux):
     {
       "mcpServers": {
         "verirag": {
           "command": "python",
           "args": ["path/to/mcp_server.py"]
         }
       }
     }
  3. Restart Claude Desktop
  4. Use @verirag in Claude to access tools

This MCP server requires:
- VeriRAG backend running (http://localhost:8000 by default)
- Bearer token for authentication (set VERIRAG_API_TOKEN env var)
"""

import os
import json
import logging
from typing import Optional
import asyncio
import httpx

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("verirag-librarian")

# Configuration
VERIRAG_API_BASE = os.environ.get("VERIRAG_API_BASE", "http://localhost:8000/api")
VERIRAG_API_TOKEN = os.environ.get("VERIRAG_API_TOKEN", "")  # Set this in your environment
DEFAULT_USER_ID = int(os.environ.get("VERIRAG_DEFAULT_USER_ID", "1"))

# HTTP client configuration
TIMEOUT = httpx.Timeout(30.0)
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {VERIRAG_API_TOKEN}" if VERIRAG_API_TOKEN else "",
}


# ============================================================================
# CORE RAG TOOLS
# ============================================================================

@mcp.tool()
async def query_library(
    question: str,
    user_id: int = DEFAULT_USER_ID,
    include_citations: bool = True,
) -> dict:
    """
    Query the VeriRAG document library with hallucination prevention.
    
    This tool searches through your uploaded documents and returns a faithful answer
    with automatic hallucination detection. If confidence is low, it regenerates
    with a backup model (Groq/Llama-3) for conservative verification.
    
    Args:
        question: Your question about the documents (e.g., "What are the key findings?")
        user_id: User ID (defaults to 1 for single-user setup)
        include_citations: Include source citations and evidence items
        
    Returns:
        dict with answer, faithfulness_score, citations, and evidence items
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{VERIRAG_API_BASE}/query/",
                json={
                    "query": question,
                    "user_id": user_id,
                },
                headers=HEADERS,
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract key fields for cleaner output
            return {
                "answer": result.get("answer", ""),
                "faithfulness_score": result.get("faithfulness_score", 0),
                "faithfulness_status": "✅ HIGH" if result.get("faithfulness_score", 0) >= 0.7
                    else "⚠️ MEDIUM" if result.get("faithfulness_score", 0) >= 0.5
                    else "❌ LOW",
                "model_used": result.get("model_used", "unknown"),
                "verification_passed": result.get("verification_passed", False),
                "explanation": result.get("explanation", ""),
                "source_citation": result.get("source_citation", "No sources cited"),
                "evidence_items": result.get("evidence_items", []) if include_citations else [],
                "context_chunks": result.get("context_chunks_used", 0),
            }
        except httpx.HTTPError as e:
            return {
                "error": f"Failed to query VeriRAG API: {str(e)}",
                "suggestion": "Ensure VeriRAG backend is running and VERIRAG_API_TOKEN is set",
            }


@mcp.tool()
async def get_document_status(
    document_id: int,
    user_id: int = DEFAULT_USER_ID,
) -> dict:
    """
    Check the indexing status and progress of a document.
    
    Use this to monitor document ingestion progress. Documents go through:
    1. PENDING: Waiting to be processed
    2. INDEXING: Currently being embedded and stored
    3. COMPLETE: Ready for queries
    4. FAILED: Indexing encountered an error
    
    Args:
        document_id: The ID of the document to check
        user_id: User ID (defaults to 1 for single-user setup)
        
    Returns:
        dict with status, progress, and error if any
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{VERIRAG_API_BASE}/documents/{document_id}/",
                headers=HEADERS,
            )
            response.raise_for_status()
            doc = response.json()
            
            return {
                "document_id": doc.get("id", document_id),
                "title": doc.get("title", "Unknown"),
                "status": doc.get("status", "unknown"),
                "progress_percent": doc.get("progress_percent", 0),
                "processed_chunks": doc.get("processed_chunks", 0),
                "total_chunks": doc.get("total_chunks", 0),
                "processed": doc.get("processed", False),
                "created_at": doc.get("created_at", ""),
                "last_error": doc.get("last_error", ""),
                "user_id": doc.get("user_id", user_id),
            }
        except httpx.HTTPError as e:
            return {
                "error": f"Failed to get document status: {str(e)}",
                "document_id": document_id,
            }


@mcp.tool()
async def list_documents(
    user_id: int = DEFAULT_USER_ID,
) -> dict:
    """
    List all documents uploaded by a user.
    
    Returns a summary of all documents: their titles, ingestion status,
    chunk counts, and created dates. Use this to see what you can query.
    
    Args:
        user_id: User ID (defaults to 1 for single-user setup)
        
    Returns:
        dict with list of documents and summary statistics
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{VERIRAG_API_BASE}/documents/",
                params={"user_id": user_id},
                headers=HEADERS,
            )
            response.raise_for_status()
            documents = response.json()
            
            # Calculate statistics
            total_docs = len(documents)
            completed_docs = sum(1 for d in documents if d.get("processed"))
            total_chunks = sum(d.get("total_chunks", 0) for d in documents)
            
            # Format document list
            doc_list = []
            for doc in documents:
                doc_list.append({
                    "id": doc.get("id"),
                    "title": doc.get("title", "Unknown"),
                    "status": doc.get("status", "unknown"),
                    "chunks": {
                        "processed": doc.get("processed_chunks", 0),
                        "total": doc.get("total_chunks", 0),
                    },
                    "progress_percent": doc.get("progress_percent", 0),
                    "created": doc.get("created_at", ""),
                })
            
            return {
                "documents": doc_list,
                "summary": {
                    "total_documents": total_docs,
                    "ready_for_query": completed_docs,
                    "total_chunks": total_chunks,
                    "percent_complete": (completed_docs / total_docs * 100) if total_docs > 0 else 0,
                },
            }
        except httpx.HTTPError as e:
            return {
                "error": f"Failed to list documents: {str(e)}",
                "suggestion": "Ensure VeriRAG backend is running",
            }


# ============================================================================
# ADVANCED TOOLS
# ============================================================================

@mcp.tool()
async def batch_query(
    questions: list[str],
    user_id: int = DEFAULT_USER_ID,
) -> dict:
    """
    Run multiple queries in batch and return aggregated results.
    
    Useful for:
    - Evaluating multiple aspects of your documents
    - Gathering data for analysis or reports
    - Testing comprehensiveness of document coverage
    
    Args:
        questions: List of questions to ask (max 10 recommended)
        user_id: User ID (defaults to 1 for single-user setup)
        
    Returns:
        dict with results for each question and aggregate statistics
    """
    results = []
    faithfulness_scores = []
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for i, question in enumerate(questions):
            try:
                response = await client.post(
                    f"{VERIRAG_API_BASE}/query/",
                    json={
                        "query": question,
                        "user_id": user_id,
                    },
                    headers=HEADERS,
                )
                response.raise_for_status()
                result = response.json()
                
                faithfulness_scores.append(result.get("faithfulness_score", 0))
                results.append({
                    "question_index": i,
                    "question": question,
                    "answer": result.get("answer", "")[:200] + "..." if len(result.get("answer", "")) > 200 else result.get("answer", ""),
                    "faithfulness": result.get("faithfulness_score", 0),
                    "verified": result.get("verification_passed", False),
                })
            except httpx.HTTPError as e:
                results.append({
                    "question_index": i,
                    "question": question,
                    "error": str(e),
                })
    
    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
    
    return {
        "queries": results,
        "statistics": {
            "total_queries": len(questions),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "average_faithfulness": avg_faithfulness,
            "high_confidence_queries": sum(1 for s in faithfulness_scores if s >= 0.7),
        },
    }


@mcp.tool()
async def analyze_document_coverage(
    document_id: int,
    topics: list[str],
    user_id: int = DEFAULT_USER_ID,
) -> dict:
    """
    Analyze how well a specific document covers given topics.
    
    Creates a query for each topic and reports coverage statistics.
    Useful for assessing completeness or relevance of documents.
    
    Args:
        document_id: Document to analyze (for context)
        topics: List of topics to check coverage for (e.g., ["security", "performance", "cost"])
        user_id: User ID
        
    Returns:
        dict with coverage analysis for each topic
    """
    coverage_results = []
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for topic in topics:
            try:
                # Craft a specific query about this topic
                query = f"What does the document say about {topic}?"
                
                response = await client.post(
                    f"{VERIRAG_API_BASE}/query/",
                    json={
                        "query": query,
                        "user_id": user_id,
                    },
                    headers=HEADERS,
                )
                response.raise_for_status()
                result = response.json()
                
                # Interpret results as coverage
                is_covered = (
                    result.get("verification_passed", False) and
                    result.get("faithfulness_score", 0) >= 0.6 and
                    "not found" not in result.get("answer", "").lower() and
                    "not mentioned" not in result.get("answer", "").lower()
                )
                
                coverage_results.append({
                    "topic": topic,
                    "covered": is_covered,
                    "confidence": result.get("faithfulness_score", 0),
                    "evidence": result.get("source_citation", "No citation found"),
                })
            except httpx.HTTPError as e:
                coverage_results.append({
                    "topic": topic,
                    "covered": False,
                    "error": str(e),
                })
    
    coverage_count = sum(1 for r in coverage_results if r.get("covered"))
    
    return {
        "document_id": document_id,
        "coverage_analysis": coverage_results,
        "summary": {
            "topics_checked": len(topics),
            "topics_covered": coverage_count,
            "coverage_percent": (coverage_count / len(topics) * 100) if topics else 0,
        },
    }


# ============================================================================
# UTILITY & HEALTH TOOLS
# ============================================================================

@mcp.tool()
async def health_check() -> dict:
    """
    Check VeriRAG backend health and connectivity.
    
    Verifies the backend is running and accessible. Use this to diagnose
    connection issues before running queries.
    
    Returns:
        dict with health status and backend information
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{VERIRAG_API_BASE}/health/",
                headers=HEADERS,
            )
            response.raise_for_status()
            health = response.json()
            
            return {
                "status": "healthy",
                "backend_reachable": True,
                "database_connected": health.get("database", {}).get("connected", False),
                "vector_store_ready": health.get("vector_store", {}).get("ready", False),
                "version": health.get("version", "unknown"),
                "api_base": VERIRAG_API_BASE,
                "authenticated": bool(VERIRAG_API_TOKEN),
            }
        except httpx.HTTPError as e:
            return {
                "status": "unhealthy",
                "backend_reachable": False,
                "error": str(e),
                "api_base": VERIRAG_API_BASE,
                "suggestion": "Check if VeriRAG backend is running on the configured API_BASE URL",
            }


@mcp.tool()
async def get_config() -> dict:
    """
    Get MCP server configuration.
    
    Shows current settings like API endpoint, user ID, and auth status.
    Useful for debugging connection issues.
    
    Returns:
        dict with current configuration
    """
    return {
        "verirag_api_base": VERIRAG_API_BASE,
        "default_user_id": DEFAULT_USER_ID,
        "authenticated": bool(VERIRAG_API_TOKEN),
        "auth_token_set": VERIRAG_API_TOKEN != "",
        "timeout_seconds": TIMEOUT.timeout,
        "environment_vars": {
            "VERIRAG_API_BASE": "Set" if os.environ.get("VERIRAG_API_BASE") else "Not set (using default)",
            "VERIRAG_API_TOKEN": "Set" if os.environ.get("VERIRAG_API_TOKEN") else "Not set",
            "VERIRAG_DEFAULT_USER_ID": "Set" if os.environ.get("VERIRAG_DEFAULT_USER_ID") else "Not set (using 1)",
        },
    }


if __name__ == "__main__":
    """Run the MCP server"""
    import sys
    
    logger.info("🚀 Starting VeriRAG MCP Server...")
    logger.info(f"📡 API Base: {VERIRAG_API_BASE}")
    logger.info(f"🔐 Authenticated: {bool(VERIRAG_API_TOKEN)}")
    
    mcp.run(transport="stdio")
