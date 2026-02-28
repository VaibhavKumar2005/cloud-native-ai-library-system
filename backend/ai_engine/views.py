import hvac
import logging
import os
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import viewsets
from rest_framework.views import APIView # <--- Added for Monitoring
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from prometheus_client import REGISTRY # <--- Added to read metrics
from ai_engine.models import Document
from ai_engine.rag_logic import get_verified_answer
from .serializers import DocumentSerializer 

logger = logging.getLogger(__name__)

def check_vault_status():
    try:
        # Using the Docker service name 'vault'
        client = hvac.Client(url='http://vault:8200')
        if client.sys.is_initialized() and not client.sys.read_seal_status()['sealed']:
            return "Unsealed"
        return "Sealed"
    except Exception as e:
        logger.error(f"Vault check failed: {e}")
        return "Unreachable"

def check_db_status():
    try:
        connections['default'].cursor()
        return "Connected"
    except OperationalError:
        return "Disconnected"

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

# --- 3. SYSTEM MISSION CONTROL API ---
class SystemInsightsView(APIView):
    """
    Endpoint for the Monitoring dashboard. 
    Retrieves telemetry from the Prometheus registry AND live infrastructure status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Pull the current values of our custom metrics defined in rag_logic.py
        rejections = REGISTRY.get_sample_value('verirag_hallucination_rejections_total') or 0
        fallbacks = REGISTRY.get_sample_value('verirag_llm_fallbacks_total') or 0
        
        # Real-time infrastructure checks
        db_status = check_db_status()
        vault_status = check_vault_status()

        # Determine overall system status
        system_status = "Operational"
        if db_status != "Connected" or vault_status != "Unsealed":
            system_status = "Degraded"

        return Response({
            "status": system_status,
            "metrics": {
                "hallucinations_prevented": int(rejections),
                "failover_recoveries": int(fallbacks),
                "active_model": "Gemini-1.5-Flash" if fallbacks == 0 else "Groq/Llama-3 (Failover Active)"
            },
            "infrastructure": {
                "database": db_status,
                "vault": vault_status,
                "orchestration": "Docker-Compose (Local Cluster)"
            }
        })