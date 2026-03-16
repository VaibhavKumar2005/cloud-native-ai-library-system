from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet,
    query_llm,
    SystemInsightsView,
    process_document,
    health_check,
    health_check_details,
)
from .ops_views import (
    cost_metrics_today,
    cost_metrics_week,
    budget_alert,
    quality_metrics_week,
    quality_metrics_month,
    ops_dashboard,
)

# The router automatically handles /documents/ for CRUD operations
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', query_llm, name='query_llm'),
    path('process-document/', process_document, name='process_document'),
    path('system-insights/', SystemInsightsView.as_view(), name='system-insights'),
    path('health/', health_check, name='health'),
    path('health/details/', health_check_details, name='health-details'),
    
    # =========================================================================
    # OPS ENDPOINTS (CostOps + QualityOps)
    # =========================================================================
    path('ops/dashboard/', ops_dashboard, name='ops_dashboard'),
    
    # Cost tracking endpoints
    path('ops/cost/today/', cost_metrics_today, name='cost_metrics_today'),
    path('ops/cost/week/', cost_metrics_week, name='cost_metrics_week'),
    path('ops/cost/budget-alert/', budget_alert, name='budget_alert'),
    
    # Quality monitoring endpoints
    path('ops/quality/week/', quality_metrics_week, name='quality_metrics_week'),
    path('ops/quality/month/', quality_metrics_month, name='quality_metrics_month'),
]
