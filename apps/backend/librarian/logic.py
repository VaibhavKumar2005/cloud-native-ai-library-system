"""
VeriRag Librarian Logic - PDF Processing and Query Interface
This module provides a simplified interface for the RAG system,
delegating to ai_engine.rag_logic for core functionality.
"""

import os
import json
import logging
from ai_engine.rag_logic import (
    ingest_document,
    process_pdf_to_vector_db,
    get_verified_answer as _get_verified_answer,
    get_api_key_from_vault,
    get_embedding_model,
    CONNECTION_STRING,
    COLLECTION_NAME,
)
from langchain_community.vectorstores import PGVector

logger = logging.getLogger(__name__)


# ============================================================================
# PUBLIC API - Simplified interfaces for external use
# ============================================================================

def process_pdf(file_path, user_id=None):
    """
    Public interface to process a PDF file into the vector database.
    
    Args:
        file_path: Path to the PDF file
        user_id: Optional user ID for multi-tenant isolation
        
    Returns:
        dict with status and message
    """
    return process_pdf_to_vector_db(file_path, user_id)


def get_verified_answer(query, user_id=None):
    """
    Public interface for querying the RAG system.
    
    Args:
        query: User's question
        user_id: User ID for tenant isolation (defaults to 'public')
        
    Returns:
        dict with answer, faithfulness_score, explanation, source_citation
    """
    if user_id is None:
        user_id = "public"
    return _get_verified_answer(query, user_id)


def list_indexed_documents(user_id=None):
    """
    Lists all documents indexed for a specific user.
    
    Args:
        user_id: User ID to filter by (None for all)
        
    Returns:
        List of document metadata
    """
    try:
        vector_db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )
        
        # Get unique document titles from the collection
        # Note: This is a simplified approach - in production you'd query the Document model
        docs = vector_db.similarity_search(
            "",  # Empty query to get all
            k=100,
            filter={"user_id": str(user_id)} if user_id else None
        )
        
        # Extract unique document titles
        unique_docs = {}
        for doc in docs:
            doc_id = doc.metadata.get('document_id', 'unknown')
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    "id": doc_id,
                    "title": doc.metadata.get('document_title', 'Unknown'),
                    "chunks": 1
                }
            else:
                unique_docs[doc_id]["chunks"] += 1
        
        return list(unique_docs.values())
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []


def get_document_context(query, user_id, k=3):
    """
    Retrieves relevant context chunks for a query without generating an answer.
    Useful for debugging and transparency.
    
    Args:
        query: Search query
        user_id: User ID for tenant isolation
        k: Number of chunks to retrieve
        
    Returns:
        List of context chunks with metadata
    """
    try:
        vector_db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )
        
        docs = vector_db.similarity_search(
            query,
            k=k,
            filter={"user_id": str(user_id)}
        )
        
        return [
            {
                "content": doc.page_content,
                "page": doc.metadata.get('page', 'Unknown'),
                "document": doc.metadata.get('document_title', 'Unknown'),
                "chunk_index": doc.metadata.get('chunk_index', 0)
            }
            for doc in docs
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        return []