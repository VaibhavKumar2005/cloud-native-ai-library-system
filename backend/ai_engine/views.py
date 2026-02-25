from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ai_engine.models import Document
from ai_engine.rag_logic import get_verified_answer
from .serializers import DocumentSerializer 

# --- 1. SECURE DOCUMENT UPLOAD ---
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    # 🚨 THE BOUNCER: Reject requests without a valid JWT
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        # TENANT ISOLATION: Users can only retrieve their own PDFs
        return Document.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # AUTO-ASSIGN: Tag the uploaded PDF with the logged-in user
        serializer.save(user=self.request.user)

# --- 2. SECURE AI CHAT ---
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 🚨 THE BOUNCER
def query_llm(request):
    user_query = request.data.get('query')
    
    if not user_query:
        return Response({"error": "No query provided"}, status=400)
    
    # Pass the authenticated user's ID down to the AI engine so it only searches their files
    result = get_verified_answer(user_query, user_id=request.user.id)
    
    return Response(result)