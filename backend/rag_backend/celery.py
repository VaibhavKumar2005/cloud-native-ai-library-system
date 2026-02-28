"""
VeriRAG Celery Configuration
Automated background task processing for document ingestion.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')

# Create Celery app
app = Celery('verirag')

# Configure using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ============================================================================
# CELERY BEAT SCHEDULE - Automated/Scheduled Tasks
# ============================================================================

app.conf.beat_schedule = {
    # Re-index unprocessed documents every 5 minutes
    'process-pending-documents': {
        'task': 'ai_engine.tasks.process_pending_documents',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'ingestion'}
    },
    
    # Health check every minute
    'system-health-check': {
        'task': 'ai_engine.tasks.system_health_check',
        'schedule': crontab(minute='*'),
        'options': {'queue': 'monitoring'}
    },
    
    # Clean up old vector embeddings weekly
    'cleanup-orphaned-vectors': {
        'task': 'ai_engine.tasks.cleanup_orphaned_vectors',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Sundays at 3 AM
        'options': {'queue': 'maintenance'}
    },
    
    # Export metrics daily
    'export-daily-metrics': {
        'task': 'ai_engine.tasks.export_daily_metrics',
        'schedule': crontab(hour=0, minute=5),  # 12:05 AM daily
        'options': {'queue': 'monitoring'}
    },
}

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

app.conf.update(
    # Task routing
    task_routes={
        'ai_engine.tasks.ingest_document_task': {'queue': 'ingestion'},
        'ai_engine.tasks.process_pending_documents': {'queue': 'ingestion'},
        'ai_engine.tasks.system_health_check': {'queue': 'monitoring'},
        'ai_engine.tasks.cleanup_orphaned_vectors': {'queue': 'maintenance'},
        'ai_engine.tasks.export_daily_metrics': {'queue': 'monitoring'},
    },
    
    # Task result settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker prefetch settings
    worker_prefetch_multiplier=1,
    
    # Result backend expiry
    result_expires=3600,
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f'Request: {self.request!r}')
    return {'status': 'Celery is working!'}
