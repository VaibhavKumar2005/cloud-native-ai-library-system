from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, query_llm, SystemInsightsView, process_document, health_check

# The router automatically handles /documents/ for CRUD operations
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', query_llm, name='query_llm'),
    path('process-document/', process_document, name='process_document'),
    path('system-insights/', SystemInsightsView.as_view(), name='system-insights'),
    path('health/', health_check, name='health'),
]