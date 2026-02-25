from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ai_engine.models import Document
from ai_engine.rag_logic import get_verified_answer
from .serializers import DocumentSerializer # assuming you have this

# 1. Secure the Document Upload/List Endpoint
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated] # 🚨 The Bouncer

    def get_queryset(self):
        # Users only see their own PDFs
        return Document.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Auto-assign the uploaded PDF to the logged-in user
        serializer.save(user=self.request.user)

# 2. Secure the Chat/AI Endpoint
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 🚨 The Bouncer
def query_llm(request):
    user_query = request.data.get('query')
    if not user_query:
        return Response({"error": "No query provided"}, status=400)
    
    # Pass the authenticated user's ID down to the AI engine
    result = get_verified_answer(user_query, user_id=request.user.id)
    return Response(result)