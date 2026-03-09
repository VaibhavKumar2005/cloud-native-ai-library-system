"""
VeriRag API Views - RESTful endpoints for the AI Library System
Provides secure document management, AI chat, and system telemetry.
"""
import logging
import os
import time
import redis
import hvac
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from prometheus_client import REGISTRY

from ai_engine.models import Document
from ai_engine.serializers import DocumentSerializer
from ai_engine.tasks import ingest_document_task
from ai_engine.rag_logic import get_verified_answer

logger = logging.getLogger(__name__)

# ============================================================================
# 1. SECURE DOCUMENT UPLOAD & MANAGEMENT
# ============================================================================

class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing PDF documents.
    Implements multi-tenant isolation via user association.
    """
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only retrieve their own documents."""
        return Document.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Auto-assign document to user and trigger async ingestion."""
        # 1. Save the document to the database
        document = serializer.save(user=self.request.user)
        
        # 2. BUG #1 FIX: Trigger ingestion via Celery worker [cite: 23, 108]
        # Using .delay() makes the API respond in milliseconds while the 
        # worker handles the 2-minute heavy lifting in the background[cite: 24, 133].
        ingest_document_task.delay(document.id) 
        
        logger.info(f"✅ Document {document.id} saved and queued for background processing.")

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Manually trigger reprocessing of a document."""
        document = self.get_object()
        ingest_document_task.delay(document.id)
        return Response({
            "status": "queued", 
            "message": f"Document {document.id} queued for re-indexing."
        })

# ============================================================================
# 2. SECURE AI CHAT ENDPOINT
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def query_llm(request):
    """Main RAG query endpoint with verification protocol."""
    user_query = request.data.get('query')
    
    if not user_query or len(user_query) > 2000:
        return Response({"error": "Invalid query length"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Execute the verification pipeline
    result = get_verified_answer(user_query, user_id=request.user.id)
    return Response(result)

# ============================================================================
# 3. PUBLIC HEALTH CHECK (for K8s & Infrastructure)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """System heartbeat check for Redis, DB, and Vault."""
    checks = {}
    overall_healthy = True

    # PostgreSQL Check
    try:
        connections['default'].cursor().execute("SELECT 1")
        checks['db'] = 'healthy'
    except Exception:
        overall_healthy = False
        checks['db'] = 'unhealthy'

    # Redis Check
    try:
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://rag-redis:6379/0'))
        r.ping()
        checks['redis'] = 'healthy'
    except Exception:
        overall_healthy = False
        checks['redis'] = 'unhealthy'

    return Response({'healthy': overall_healthy, 'services': checks}, 
                    status=status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE)