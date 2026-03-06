"""
VeriRag API Views - RESTful endpoints for the AI Library System
Provides secure document management, AI chat, and system telemetry.
"""

import hvac
import logging
import os
import time
import redis
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from prometheus_client import REGISTRY
from ai_engine.models import Document
from ai_engine.rag_logic import get_verified_answer, ingest_document
from .serializers import DocumentSerializer

logger = logging.getLogger(__name__)


# ============================================================================
# INFRASTRUCTURE HEALTH CHECKS
# ============================================================================

def check_vault_status():
    """Check HashiCorp Vault connectivity and seal status."""
    try:
        vault_url = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
        client = hvac.Client(url=vault_url)
        
        if not client.sys.is_initialized():
            return "Uninitialized"
        
        seal_status = client.sys.read_seal_status()
        if seal_status['sealed']:
            return "Sealed"
        
        return "Unsealed"
        
    except Exception as e:
        logger.error(f"Vault check failed: {e}")
        return "Unreachable"


def check_db_status():
    """Check PostgreSQL database connectivity."""
    try:
        connections['default'].cursor()
        return "Connected"
    except OperationalError:
        return "Disconnected"


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
        """Auto-assign uploaded document to the authenticated user."""
        document = serializer.save(user=self.request.user)
        
        # Trigger automatic ingestion after upload
        try:
            result = ingest_document(document.id)
            if result.get('status') == 'success':
                logger.info(f"✅ Auto-ingested document {document.id}")
            else:
                logger.warning(f"⚠️ Auto-ingestion failed for {document.id}: {result.get('message')}")
        except Exception as e:
            logger.error(f"❌ Auto-ingestion error for {document.id}: {e}")

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Manually trigger reprocessing of a document."""
        document = self.get_object()
        result = ingest_document(document.id)
        return Response(result)


# ============================================================================
# 2. SECURE AI CHAT ENDPOINT
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def query_llm(request):
    """
    Main RAG query endpoint with full verification protocol.
    
    Request body:
        - query: string (required) - The user's question
        
    Response:
        - answer: string - The AI-generated response
        - faithfulness_score: float - Confidence score (0.0-1.0)
        - explanation: string - Why this score was given
        - source_citation: string - Document references
        - verification_passed: bool - Whether faithfulness threshold was met
        - model_used: string - Which LLM generated the response
        - context_chunks_used: int - Number of context chunks retrieved
    """
    user_query = request.data.get('query')
    
    if not user_query:
        return Response(
            {"error": "No query provided", "details": "Include 'query' in request body"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(user_query) > 2000:
        return Response(
            {"error": "Query too long", "details": "Maximum query length is 2000 characters"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Execute the verification pipeline
    result = get_verified_answer(user_query, user_id=request.user.id)
    
    # Ensure standardized response format
    standardized_response = {
        "answer": result.get("answer", "Unable to generate response"),
        "faithfulness_score": result.get("faithfulness_score", 0.0),
        "explanation": result.get("explanation", ""),
        "source_citation": result.get("source_citation", "None"),
        "verification_passed": result.get("verification_passed", False),
        "model_used": result.get("model_used", "unknown"),
        "context_chunks_used": result.get("context_chunks_used", 0),
        "metadata": {
            "user_id": request.user.id,
            "query_length": len(user_query)
        }
    }
    
    return Response(standardized_response)


# ============================================================================
# 3. SYSTEM MISSION CONTROL API
# ============================================================================

class SystemInsightsView(APIView):
    """
    Endpoint for the Monitoring dashboard.
    Retrieves telemetry from Prometheus registry and live infrastructure status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /api/system-insights/
        
        Returns system health, AI metrics, and infrastructure status.
        """
        # Pull custom metrics from Prometheus registry
        rejections = REGISTRY.get_sample_value('verirag_hallucination_rejections_total') or 0
        fallbacks = REGISTRY.get_sample_value('verirag_llm_fallbacks_total') or 0
        queries_total = REGISTRY.get_sample_value('verirag_queries_total') or 0
        docs_ingested = REGISTRY.get_sample_value('verirag_documents_ingested_total') or 0
        
        # Real-time infrastructure checks
        db_status = check_db_status()
        vault_status = check_vault_status()

        # Determine overall system status
        system_status = "Operational"
        status_details = []
        
        if db_status != "Connected":
            system_status = "Degraded"
            status_details.append("Database disconnected")
        
        if vault_status not in ["Unsealed", "Unreachable"]:
            # Allow unreachable vault in dev mode with env fallback
            if os.environ.get('DEBUG', 'False') == 'True':
                pass  # Acceptable in development
            else:
                system_status = "Degraded"
                status_details.append(f"Vault status: {vault_status}")
        
        if rejections > 10 and queries_total > 0:
            rejection_rate = rejections / queries_total
            if rejection_rate > 0.3:
                status_details.append(f"High hallucination rate: {rejection_rate:.1%}")

        # Calculate uptime approximation (simplified)
        uptime_score = 100
        if db_status != "Connected":
            uptime_score -= 40
        if vault_status == "Sealed":
            uptime_score -= 30
        if system_status == "Degraded":
            uptime_score -= 10

        return Response({
            "status": system_status,
            "status_details": status_details if status_details else ["All systems nominal"],
            "metrics": {
                "hallucinations_prevented": int(rejections),
                "failover_recoveries": int(fallbacks),
                "total_queries": int(queries_total),
                "documents_ingested": int(docs_ingested),
                "active_model": "Gemini-1.5-Flash" if fallbacks == 0 else "Groq/Llama-3 (Failover Active)",
                "verification_threshold": 0.6
            },
            "infrastructure": {
                "database": db_status,
                "vault": vault_status,
                "orchestration": "Docker-Compose (Local Cluster)",
                "uptime_score": max(0, uptime_score)
            }
        })


# ============================================================================
# 4. DOCUMENT PROCESSING ENDPOINT
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_document(request):
    """
    Manually trigger document processing/re-ingestion.
    
    Request body:
        - document_id: int (required) - ID of the document to process
    """
    doc_id = request.data.get('document_id')
    
    if not doc_id:
        return Response(
            {"error": "document_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify ownership
    try:
        doc = Document.objects.get(id=doc_id, user=request.user)
    except Document.DoesNotExist:
        return Response(
            {"error": "Document not found or access denied"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = ingest_document(doc_id)
    
    return Response({
        "document_id": doc_id,
        "title": doc.title,
        "status": result.get("status"),
        "message": result.get("message"),
        "chunks_created": result.get("chunks_created", 0)
    })


# ============================================================================
# 5. PUBLIC HEALTH CHECK (for K8s Probes & Load Balancers)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/health/

    Public endpoint for Kubernetes readiness/liveness probes.
    Checks Redis, PostgreSQL, and Vault in parallel and returns
    per-service status with latency measurements.
    """
    checks = {}
    overall_healthy = True

    # ── PostgreSQL ───────────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        connections['default'].cursor().execute("SELECT 1")
        checks['postgresql'] = {
            'status': 'healthy',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
        }
    except Exception as e:
        overall_healthy = False
        checks['postgresql'] = {
            'status': 'unhealthy',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
            'error': str(e),
        }

    # ── Redis ────────────────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
        r = redis.from_url(redis_url, socket_connect_timeout=3)
        r.ping()
        checks['redis'] = {
            'status': 'healthy',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
        }
    except Exception as e:
        overall_healthy = False
        checks['redis'] = {
            'status': 'unhealthy',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
            'error': str(e),
        }

    # ── HashiCorp Vault ──────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        vault_url = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
        client = hvac.Client(url=vault_url)
        seal_status = client.sys.read_seal_status()
        vault_healthy = not seal_status.get('sealed', True)
        checks['vault'] = {
            'status': 'healthy' if vault_healthy else 'sealed',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
        }
        if not vault_healthy:
            overall_healthy = False
    except Exception as e:
        # Vault being unreachable is a warning, not necessarily fatal
        checks['vault'] = {
            'status': 'unreachable',
            'latency_ms': round((time.monotonic() - t0) * 1000, 2),
            'error': str(e),
        }
        # In dev mode, don't fail health for vault
        if os.environ.get('DEBUG', 'False') != 'True':
            overall_healthy = False

    http_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response({
        'healthy': overall_healthy,
        'services': checks,
    }, status=http_status)