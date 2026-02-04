from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .rag_logic import get_verified_answer, ingest_document
from .models import Document

@api_view(['POST'])
def query_llm(request):
    """
    Primary RAG Endpoint for VeriRag.
    Receives: {'query': 'user question'}
    Returns: AI Answer + Faithfulness Score
    """
    user_query = request.data.get('query', '')
    
    if not user_query:
        return Response({
            "answer": "Please provide a query.",
            "faithfulness_score": 0,
            "explanation": "No query provided",
            "source_citation": "None"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Call the actual RAG logic
    result = get_verified_answer(user_query)
    return Response(result)

@api_view(['POST'])
def upload_document(request):
    """
    Upload PDF documents for ingestion into the RAG system.
    """
    if 'file' not in request.FILES:
        return Response({
            "error": "No file provided"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    title = request.data.get('title', file.name)
    
    # Create document record
    doc = Document.objects.create(
        title=title,
        file=file
    )
    
    # Trigger ingestion
    try:
        success = ingest_document(doc.id)
        if success:
            return Response({
                "message": "Document uploaded and processed successfully",
                "document_id": doc.id,
                "title": doc.title
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "error": "Document uploaded but processing failed"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            "error": f"Processing failed: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def list_documents(request):
    """
    List all uploaded documents.
    """
    docs = Document.objects.all().order_by('-uploaded_at')
    return Response([
        {
            "id": doc.id,
            "title": doc.title,
            "uploaded_at": doc.uploaded_at,
            "processed": doc.processed
        } for doc in docs
    ])