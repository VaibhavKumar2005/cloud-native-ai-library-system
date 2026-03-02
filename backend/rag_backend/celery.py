import os
from celery import Celery

# Set the default Django settings module for the Celery program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')

# Create the Celery app instance
app = Celery('rag_backend')

# Load Celery config from Django settings using the CELERY_ namespace prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')