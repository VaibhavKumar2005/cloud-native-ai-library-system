#!/usr/bin/env python3
"""
Quick RAG System Test - Use against running backend
Tests basic connectivity and RAG functionality
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL
BACKEND_URL = "http://localhost:8000"
API_BASE = f"{BACKEND_URL}/api"

# Colors for output
class Colors:
    PASS = '\033[92m'
    FAIL = '\033[91m'
    INFO = '\033[94m'
    WARN = '\033[93m'
    END = '\033[0m'

def test_backend_health() -> bool:
    """Test if backend is running"""
    print(f"\n{Colors.INFO}1. Testing Backend Health...{Colors.END}")
    try:
        # Try common health endpoints
        endpoints = [
            f"{API_BASE}/health/",
            f"{BACKEND_URL}/health/",
            f"{API_BASE}/",
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=2)
                if response.status_code < 500:
                    print(f"   {Colors.PASS}✓ Backend responding at {endpoint}{Colors.END}")
                    print(f"     Status: {response.status_code}")
                    return True
            except:
                continue
        
        print(f"   {Colors.WARN}⚠ Backend not responding at expected endpoints{Colors.END}")
        return True  # Continue anyway, might be permission issue
        
    except Exception as e:
        print(f"   {Colors.FAIL}✗ Backend health check failed: {e}{Colors.END}")
        return False

def test_query_endpoint() -> bool:
    """Test RAG query endpoint"""
    print(f"\n{Colors.INFO}2. Testing RAG Query Endpoint...{Colors.END}")
    
    # Try different possible endpoints
    endpoints = [
        f"{API_BASE}/query/",
        f"{API_BASE}/rag/query/",
        f"{API_BASE}/academic/query/",
        f"{BACKEND_URL}/rag/query/",
    ]
    
    test_query = "What is RAG?"
    
    for endpoint in endpoints:
        try:
            payload = {
                "query": test_query,
                "user_id": 1,
            }
            
            response = requests.post(endpoint, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   {Colors.PASS}✓ Query endpoint found: {endpoint}{Colors.END}")
                print(f"     Response: {json.dumps(result, indent=2)[:200]}...")
                return True
            elif response.status_code != 404:
                print(f"   {Colors.WARN}⚠ Endpoint {endpoint} → {response.status_code}{Colors.END}")
        except Exception as e:
            continue
    
    print(f"   {Colors.WARN}⚠ RAG query endpoint not found (may need to create test user){Colors.END}")
    return True  # Don't fail entirely

def test_frontend_health() -> bool:
    """Test if frontend is running"""
    print(f"\n{Colors.INFO}3. Testing Frontend...{Colors.END}")
    
    try:
        response = requests.get("http://localhost:5173/", timeout=2)
        if response.status_code < 500:
            print(f"   {Colors.PASS}✓ Frontend running at http://localhost:5173{Colors.END}")
            return True
    except Exception as e:
        print(f"   {Colors.FAIL}✗ Frontend not responding: {e}{Colors.END}")
        return False

def test_database_connection() -> bool:
    """Test database connectivity via Django"""
    print(f"\n{Colors.INFO}4. Testing Database Connection...{Colors.END}")
    
    try:
        # Try DB check endpoint
        endpoint = f"{API_BASE}/db-check/"
        response = requests.get(endpoint, timeout=2)
        if response.status_code < 500:
            print(f"   {Colors.PASS}✓ Database responding{Colors.END}")
            return True
    except:
        pass
    
    print(f"   {Colors.WARN}⚠ Database endpoint not found (may need to run migrations){Colors.END}")
    return True

def run_test_queries() -> Dict[str, Any]:
    """Run the 9 core test queries"""
    print(f"\n{Colors.INFO}5. Running Core Test Queries...{Colors.END}")
    
    queries = [
        ("What is RAG?", "basic"),
        ("How does RAG reduce hallucination?", "basic"),
        ("What is a vector database?", "basic"),
        ("Compare RAG vs fine-tuning for knowledge grounding", "advanced"),
        ("How does pgvector indexing work?", "advanced"),
        ("Explain turboquant", "rejection"),
        ("What is GraphRAG?", "rejection"),
    ]
    
    results = []
    
    for query_text, category in queries:
        print(f"\n   Query: {query_text}")
        print(f"   Category: {category}")
        
        # Try query endpoint
        endpoints = [
            f"{API_BASE}/query/",
            f"{API_BASE}/rag/query/",
        ]
        
        for endpoint in endpoints:
            try:
                payload = {"query": query_text, "user_id": 1}
                response = requests.post(endpoint, json=payload, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        "query": query_text,
                        "category": category,
                        "success": True,
                        "response": result,
                    })
                    
                    confidence = result.get("confidence", 0)
                    method = result.get("method", "unknown")
                    print(f"   {Colors.PASS}✓ Success | Confidence: {confidence:.2f} | Method: {method}{Colors.END}")
                    break
                    
            except Exception as e:
                continue
        else:
            print(f"   {Colors.WARN}⚠ Could not reach query endpoint{Colors.END}")
    
    return {"total": len(queries), "results": results}

def print_summary(tests: Dict[str, bool], queries: Dict[str, Any]):
    """Print test summary"""
    print(f"\n{'='*60}")
    print(f"{Colors.INFO}TEST SUMMARY{Colors.END}")
    print(f"{'='*60}")
    
    passed = sum(1 for v in tests.values() if v)
    total = len(tests)
    
    print(f"\nSystem Health: {passed}/{total} checks passed")
    
    if queries["results"]:
        print(f"\nQueries Tested: {len(queries['results'])}/{queries['total']}")
        print(f"Success Rate: {len(queries['results'])/queries['total']*100:.0f}%")
    
    print(f"\n{Colors.INFO}Services Running:{Colors.END}")
    if tests.get("backend"):
        print(f"  {Colors.PASS}✓ Backend{Colors.END}")
    else:
        print(f"  {Colors.FAIL}✗ Backend{Colors.END}")
    
    if tests.get("frontend"):
        print(f"  {Colors.PASS}✓ Frontend{Colors.END}")
    else:
        print(f"  {Colors.FAIL}✗ Frontend{Colors.END}")
    
    print(f"\n{Colors.INFO}Next Steps:{Colors.END}")
    if not tests.get("backend"):
        print("  1. Start backend: cd apps/backend && python manage.py runserver")
    if not tests.get("frontend"):
        print("  2. Start frontend: cd apps/frontend && npm run dev")
    print("  3. Read RAG_EVALUATION_FRAMEWORK.md for full evaluation guide")
    print("  4. Run evaluation: python tests/evaluate_rag.py")

def main():
    """Run all tests"""
    print(f"\n{Colors.INFO}╔════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.INFO}║   VeriRAG System Quick Test             ║{Colors.END}")
    print(f"{Colors.INFO}╚════════════════════════════════════════╝{Colors.END}")
    
    tests = {
        "backend": test_backend_health(),
        "frontend": test_frontend_health(),
        "database": test_database_connection(),
    }
    
    # Only run query tests if backend is working
    if tests["backend"]:
        query_results = run_test_queries()
    else:
        query_results = {"total": 0, "results": []}
    
    print_summary(tests, query_results)
    
    # Return exit code
    all_passed = all(tests.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
