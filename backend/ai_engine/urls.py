from django.urls import path
from .views import query_llm, upload_document, list_documents

urlpatterns = [
    path('query/', query_llm, name='query_llm'),
    path('upload/', upload_document, name='upload_document'),
    path('documents/', list_documents, name='list_documents'),
]