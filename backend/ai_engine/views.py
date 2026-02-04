from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def query_llm(request):
    """
    Primary RAG Endpoint for VeriRag.
    Receives: {'query': 'user question'}
    Returns: AI Answer + Faithfulness Score
    """
    user_query = request.data.get('query', 'No query provided')
    
    # MOCK RESPONSE: We will swap this for Gemini logic next.
    return Response({
        "answer": f"System Active. Analyzing CS Library for: '{user_query}'...",
        "faithfulness_score": 0.98,
        "source_citation": "Verified via Librarian-RAG Engine (Project 46)."
    })