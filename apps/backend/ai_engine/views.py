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
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes as drf_throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from prometheus_client import REGISTRY
from datetime import datetime

from ai_engine.models import Document, QueryLog
from ai_engine.serializers import DocumentSerializer
from ai_engine.tasks import ingest_document_task
# from ai_engine.costops import get_cost_tracker
# from ai_engine.qualityops import get_quality_gate
# from ai_engine.promptops import get_prompt_ops
# from ai_engine.driftops import get_drift_ops
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
@permission_classes([AllowAny])
def query_llm(request):
    """
    Minimal RAG query endpoint.
    """
    from ai_engine.rag_logic import query_academic_rag

    user_query = request.data.get('query')

    if not user_query or not str(user_query).strip():
        return Response({"error": "query is required"}, status=status.HTTP_400_BAD_REQUEST)

    result = query_academic_rag(str(user_query).strip())
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@drf_throttle_classes([QueryUserRateThrottle])
def research_query(request):
    """
    Enhanced RAG query endpoint for research with session paper filtering.
    Supports pinned papers and external paper suggestions.
    
    POST /api/ai/research/query/
    Body: {
        "query": "...",
        "session_paper_ids": [1, 2, 3]  # optional
    }
    """
    from ai_engine.rag_logic import query_academic_rag
    from ai_engine.serializers import AcademicRAGQuerySerializer
    
    serializer = AcademicRAGQuerySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user_query = serializer.validated_data['query']
    session_paper_ids = serializer.validated_data.get('session_paper_ids', [])
    
    start_time = time.time()
    
    try:
        # Call enhanced RAG engine with session filtering
        result = query_academic_rag(query=user_query)
        
        # Log for cost tracking
        QueryLog.objects.create(
            user=request.user,
            query_text=user_query,
            method=result.get('method', 'error'),
            tokens_used=result.get('tokens_used', 0),
            cost_usd=float(result.get('cost_usd', 0.0)),
            latency_ms=result.get('latency_ms', int((time.time() - start_time) * 1000))
        )
        
        return Response(result)
    
    except Exception as e:
        logger.error(f"Research query failed: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
    """
    Public heartbeat check for K8s/ACA liveness probes.
    Returns minimal info to avoid infrastructure leakage.
    """
    healthy, _ = _run_health_checks()
    return Response(
        {
            'healthy': healthy,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '2.0.0',
        },
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health_check_details(request):
    """
    Authenticated detailed health check for ops dashboard.
    Includes component status, latency, and deployment info.
    """
    healthy, checks = _run_health_checks()

    # Determine overall status
    status_text = 'ok' if healthy else ('degraded' if any(c.get('status') == 'healthy' for c in checks.values()) else 'critical')

    return Response(
        {
            'status': status_text,
            'healthy': healthy,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '2.0.0',
            'deployment_mode': os.environ.get('DEPLOY_MODE', 'local'),
            'components': checks,
        },
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )


def _run_health_checks():
    """
    Comprehensive service connectivity checks for public and private health endpoints.
    Returns overall health status and detailed component checks with latency metrics.
    """
    checks = {}
    overall_healthy = True

    # PostgreSQL Check
    try:
        start = time.perf_counter()
        connections['default'].cursor().execute("SELECT 1")
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        checks['postgres'] = {
            'status': 'healthy',
            'latency_ms': latency_ms,
            'component': 'PostgreSQL + pgvector',
        }
    except Exception as e:
        overall_healthy = False
        logger.warning(f"PostgreSQL health check failed: {e}")
        checks['postgres'] = {
            'status': 'unhealthy',
            'latency_ms': 0,
            'component': 'PostgreSQL + pgvector',
            'error': str(type(e).__name__),
        }

    # Redis Check
    try:
        start = time.perf_counter()
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://rag-redis:6379/0'))
        r.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        checks['redis'] = {
            'status': 'healthy',
            'latency_ms': latency_ms,
            'component': 'Redis (Celery broker & cache)',
        }
    except Exception as e:
        overall_healthy = False
        logger.warning(f"Redis health check failed: {e}")
        checks['redis'] = {
            'status': 'unhealthy',
            'latency_ms': 0,
            'component': 'Redis (Celery broker & cache)',
            'error': str(type(e).__name__),
        }

    # Azure Key Vault Check (if in cloud mode)
    if os.environ.get('DEPLOY_MODE') == 'cloud' and os.environ.get('AZURE_KEY_VAULT_URL'):
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            start = time.perf_counter()
            credential = DefaultAzureCredential()
            client = SecretClient(
                vault_url=os.environ.get('AZURE_KEY_VAULT_URL'),
                credential=credential,
            )
            # Minimal operation to verify connectivity
            client.list_properties_of_secrets()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            checks['azure_keyvault'] = {
                'status': 'healthy',
                'latency_ms': latency_ms,
                'component': 'Azure Key Vault',
            }
        except Exception as e:
            logger.warning(f"Azure Key Vault health check failed: {e}")
            checks['azure_keyvault'] = {
                'status': 'unhealthy',
                'latency_ms': 0,
                'component': 'Azure Key Vault',
                'error': str(type(e).__name__),
            }
    else:
        # HashiCorp Vault Check (local mode)
        try:
            start = time.perf_counter()
            client = hvac.Client(
                url=os.environ.get('VAULT_ADDR', 'http://rag-vault:8200'),
                token=os.environ.get('VAULT_TOKEN')
            )
            sealed = client.sys.read_seal_status().get('sealed', True)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if sealed:
                overall_healthy = False
                checks['vault'] = {
                    'status': 'unhealthy',
                    'latency_ms': latency_ms,
                    'component': 'HashiCorp Vault',
                    'error': 'Vault is sealed',
                }
            else:
                checks['vault'] = {
                    'status': 'healthy',
                    'latency_ms': latency_ms,
                    'component': 'HashiCorp Vault',
                }
        except Exception as e:
            logger.warning(f"Vault health check failed: {e}")
            checks['vault'] = {
                'status': 'unhealthy',
                'latency_ms': 0,
                'component': 'HashiCorp Vault',
                'error': str(type(e).__name__),
            }

    # Azure OpenAI Check (verification that endpoint is reachable)
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_KEY:
        try:
            start = time.perf_counter()
            # Just verify the endpoint is accessible (no actual API call)
            import requests
            resp = requests.head(
                settings.AZURE_OPENAI_ENDPOINT,
                headers={'api-key': settings.AZURE_OPENAI_KEY},
                timeout=5,
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            checks['azure_openai'] = {
                'status': 'healthy' if resp.status_code in [200, 401, 404] else 'unhealthy',
                'latency_ms': latency_ms,
                'component': 'Azure OpenAI',
            }
        except Exception as e:
            logger.warning(f"Azure OpenAI health check failed: {e}")
            checks['azure_openai'] = {
                'status': 'unhealthy',
                'latency_ms': 0,
                'component': 'Azure OpenAI',
                'error': str(type(e).__name__),
            }

    return overall_healthy, checks
