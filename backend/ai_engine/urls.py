from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, query_llm, SystemInsightsView # <--- Added SystemInsightsView here

# The router automatically handles /documents/ for listing and uploading
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', query_llm, name='query_llm'),
    path('system-insights/', SystemInsightsView.as_view(), name='system-insights'),
]