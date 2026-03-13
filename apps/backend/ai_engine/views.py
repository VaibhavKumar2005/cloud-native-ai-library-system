"""
VeriRag API Views - RESTful endpoints for the AI Library System
Provides secure document management, AI chat, and system telemetry.
"""
import logging
import os
import time
import uuid
import redis
import hvac
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes as drf_throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from prometheus_client import REGISTRY

from ai_engine.models import Document
from ai_engine.serializers import DocumentSerializer
from ai_engine.tasks import ingest_document_task
from ai_engine.rag_logic import get_verified_answer
from ai_engine.throttles import (
    QueryUserRateThrottle,
    UploadUserRateThrottle,
    DocumentActionUserRateThrottle,
)
from ai_engine.tracing import add_span_attributes, get_trace_id, record_event, trace_context

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
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadUserRateThrottle]

    def get_queryset(self):
        """Users can only retrieve their own documents."""
        return Document.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Auto-assign document to user and trigger async ingestion."""
        # 1. Save the document to the database
        document = serializer.save(
            user=self.request.user,
            processed=False,
            status=Document.Status.QUEUED,
            progress_percent=0,
            total_chunks=0,
            processed_chunks=0,
            last_error='',
        )

        try:
            # Using .delay() keeps upload latency low while the worker handles indexing.
            ingest_document_task.delay(document.id)
            logger.info(f"✅ Document {document.id} saved and queued for background processing.")
        except Exception as exc:
            # Queue outages should not block the file upload itself.
            logger.exception("Failed to queue ingestion for document %s: %s", document.id, exc)

    @action(detail=True, methods=['post'])
    @drf_throttle_classes([DocumentActionUserRateThrottle])
    def reprocess(self, request, pk=None):
        """Manually trigger reprocessing of a document."""
        document = self.get_object()
        document.processed = False
        document.status = Document.Status.QUEUED
        document.progress_percent = 0
        document.total_chunks = 0
        document.processed_chunks = 0
        document.last_error = ''
        document.save(update_fields=[
            'processed',
            'status',
            'progress_percent',
            'total_chunks',
            'processed_chunks',
            'last_error',
        ])
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
@drf_throttle_classes([QueryUserRateThrottle])
def query_llm(request):
    """Main RAG query endpoint with verification protocol."""
    user_query = request.data.get('query')
    
    if not user_query or len(user_query) > 2000:
        return Response({"error": "Invalid query length"}, status=status.HTTP_400_BAD_REQUEST)

    query_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    started_at = time.perf_counter()

    with trace_context(
        "rag.query.request",
        {
            "enduser.id": request.user.id,
            "rag.query.id": query_id,
            "rag.query.length": len(user_query),
            "http.route": request.path,
        },
    ):
        add_span_attributes(
            {
                "rag.query.id": query_id,
                "rag.query.preview": user_query[:120],
            }
        )
        record_event("rag.query.received", {"rag.query.id": query_id})
        result = get_verified_answer(
            user_query,
            user_id=request.user.id,
            request_context={
                "query_id": query_id,
                "request_path": request.path,
                "trace_id": get_trace_id(),
            },
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        trace_id = get_trace_id()
        result["query_id"] = query_id
        result["trace_id"] = trace_id
        result["latency_ms"] = latency_ms
        add_span_attributes(
            {
                "rag.response.trace_id": trace_id or "",
                "rag.response.latency_ms": latency_ms,
                "rag.response.verification_passed": result.get("verification_passed", False),
                "rag.response.model_used": result.get("model_used", "unknown"),
            }
        )
        record_event(
            "rag.query.completed",
            {
                "rag.query.id": query_id,
                "rag.response.model_used": result.get("model_used", "unknown"),
                "rag.response.verification_passed": result.get("verification_passed", False),
            },
        )

    response = Response(result)
    if trace_id:
        response["X-Trace-Id"] = trace_id
    response["X-Query-Id"] = query_id
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@drf_throttle_classes([DocumentActionUserRateThrottle])
def process_document(request):
    """Queue asynchronous processing for an existing uploaded document."""
    doc_id = request.data.get('document_id')
    if not doc_id:
        return Response({"error": "document_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        document = Document.objects.get(id=doc_id, user=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    document.processed = False
    document.status = Document.Status.QUEUED
    document.progress_percent = 0
    document.total_chunks = 0
    document.processed_chunks = 0
    document.last_error = ''
    document.save(update_fields=[
        'processed',
        'status',
        'progress_percent',
        'total_chunks',
        'processed_chunks',
        'last_error',
    ])
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
    """Public heartbeat check that avoids leaking infrastructure internals."""
    healthy, _ = _run_health_checks()
    return Response(
        {'healthy': healthy},
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health_check_details(request):
    """Authenticated detailed health check for operational debugging."""
    healthy, checks = _run_health_checks()
    return Response(
        {'healthy': healthy, 'services': checks},
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )


def _run_health_checks():
    """Shared service connectivity checks used by public and private health endpoints."""
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

    return overall_healthy, checks
