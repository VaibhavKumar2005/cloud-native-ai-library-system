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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_document(request):
    """Queue asynchronous processing for an existing uploaded document."""
    doc_id = request.data.get('document_id')
    if not doc_id:
        return Response({"error": "document_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        document = Document.objects.get(id=doc_id, user=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    ingest_document_task.delay(document.id)
    return Response({"status": "queued", "document_id": document.id}, status=status.HTTP_202_ACCEPTED)


class SystemInsightsView(APIView):
    """Expose lightweight telemetry used by the frontend monitoring dashboard."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        metrics = []
        for metric in REGISTRY.collect():
            metrics.append(
                {
                    "name": metric.name,
                    "samples": [
                        {"name": s.name, "labels": s.labels, "value": s.value}
                        for s in metric.samples
                    ],
                }
            )
        return Response({"metrics": metrics})

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
        start = time.perf_counter()
        connections['default'].cursor().execute("SELECT 1")
        checks['postgresql'] = {
            'status': 'healthy',
            'latency_ms': round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception:
        overall_healthy = False
        checks['postgresql'] = {'status': 'unhealthy', 'latency_ms': 0}

    # Redis Check
    try:
        start = time.perf_counter()
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://rag-redis:6379/0'))
        r.ping()
        checks['redis'] = {
            'status': 'healthy',
            'latency_ms': round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception:
        overall_healthy = False
        checks['redis'] = {'status': 'unhealthy', 'latency_ms': 0}

    # Vault Check
    try:
        start = time.perf_counter()
        client = hvac.Client(
            url=os.environ.get('VAULT_ADDR', 'http://rag-vault:8200'),
            token=os.environ.get('VAULT_TOKEN')
        )
        sealed = client.sys.read_seal_status().get('sealed', True)
        if sealed:
            overall_healthy = False
            checks['vault'] = {'status': 'unhealthy', 'latency_ms': round((time.perf_counter() - start) * 1000, 2)}
        else:
            checks['vault'] = {'status': 'healthy', 'latency_ms': round((time.perf_counter() - start) * 1000, 2)}
    except Exception:
        overall_healthy = False
        checks['vault'] = {'status': 'unhealthy', 'latency_ms': 0}

    return Response({'healthy': overall_healthy, 'services': checks}, 
                    status=status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE)
