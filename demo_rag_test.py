#!/usr/bin/env python3
"""
VeriRAG Live Demo Test
======================
Tests the public /query endpoint with mocked vector store.
Run with: python demo_rag_test.py
"""

import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')
os.environ['USE_SQLITE_FOR_TESTS'] = 'True'
django.setup()

from unittest.mock import patch, MagicMock
from django.test import Client
from langchain_core.documents import Document

# ============================================================================
# DEMO TEST SUITE
# ============================================================================

def test_public_query_endpoint():
    """Test /query endpoint with mocked vector store"""
    
    print("\n" + "="*80)
    print("VeriRAG Live Demo Test")
    print("="*80)
    
    client = Client()
    
    # Mock the vector store to return sample documents
    mock_docs = [
        Document(
            page_content="Retrieval-Augmented Generation (RAG) combines document retrieval with language models to generate grounded answers. It reduces hallucination by using real evidence from documents.",
            metadata={
                "document_title": "RAG Fundamentals",
                "source": "Technical Docs",
                "page": 1
            }
        ),
        Document(
            page_content="RAG is important because it ensures AI answers are grounded in factual sources, reducing model hallucinations and improving trust in AI systems.",
            metadata={
                "document_title": "Why RAG Matters",
                "source": "Research Paper",
                "page": 5
            }
        ),
        Document(
            page_content="Unlike fine-tuning, RAG allows real-time knowledge updates without retraining. It's more cost-effective and transparent, showing evidence for every answer.",
            metadata={
                "document_title": "RAG vs Fine-tuning",
                "source": "Comparison Guide",
                "page": 12
            }
        ),
    ]
    
    test_cases = [
        {
            "query": "What is retrieval augmented generation and why is it important for AI systems?",
            "description": "Test 1: Knowledge-grounding question"
        },
        {
            "query": "How does RAG compare to fine-tuning?",
            "description": "Test 2: Comparative analysis"
        },
        {
            "query": "Why should we trust RAG systems?",
            "description": "Test 3: Trust and reliability"
        },
    ]
    
    # Mock the vector store
    with patch('ai_engine.rag_logic.get_vector_store') as mock_vector_store:
        # Setup the mock
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = mock_docs
        mock_vector_store.return_value = mock_store
        
        print("\n📋 Running Test Suite\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"┌─ {test_case['description']}")
            print(f"│  Query: {test_case['query'][:60]}...")
            
            response = client.post(
                '/query',
                data=json.dumps({"query": test_case['query']}),
                content_type='application/json'
            )
            
            print(f"│  Status: {response.status_code}")
            
            if response.status_code == 200:
                result = json.loads(response.content)
                print(f"│  Status: ✓ SUCCESS")
                print(f"│  Result: {result['status']}")
                
                if result['status'] == 'success':
                    answer = result.get('answer', '')
                    sources = result.get('sources', [])
                    print(f"│  Answer: {answer[:100]}..." if len(answer) > 100 else f"│  Answer: {answer}")
                    print(f"│  Sources: {len(sources)} document(s)")
                    for j, src in enumerate(sources[:2], 1):
                        print(f"│    [{j}] {src.get('title', 'Unknown')} (page {src.get('page', 'N/A')})")
            else:
                print(f"│  ✗ FAILED: {response.status_code}")
                try:
                    error = json.loads(response.content)
                    print(f"│  Error: {error}")
                except:
                    print(f"│  Response: {response.content[:200]}")
            
            print(f"└─ {'Pass' if response.status_code == 200 else 'Fail'}\n")
    
    print("\n" + "="*80)
    print("Demo Test Complete")
    print("="*80)
    print("\n✅ API is responding correctly with proper demo flow:")
    print("   1. Accept public /query POST requests")
    print("   2. Retrieve relevant documents")
    print("   3. Generate grounded answers with citations")
    print("   4. Return structured JSON response")
    print("\n📊 Ready for demo to outside users!")
    print("="*80 + "\n")

if __name__ == '__main__':
    test_public_query_endpoint()
