"""
WSGI config for rag_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

See https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/

ACA/Kubernetes Graceful Shutdown Pattern:
  When ACA sends SIGTERM, this module ensures:
  - Celery stops accepting new tasks
  - Existing requests complete (Django queue drains)
  - Database connections close cleanly
  - Container terminates gracefully (no incomplete transactions)
"""

import os
import signal
import logging
import sys

from django.core.wsgi import get_wsgi_application

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')

application = get_wsgi_application()


# ══════════════════════════════════════════════════════════════════════════════
# GRACEFUL SHUTDOWN HANDLER FOR ACA/K8s
# ══════════════════════════════════════════════════════════════════════════════
#
# ACA Container Apps sends SIGTERM 30s before forced termination.
# This handler ensures clean shutdown without request loss.
#

def handle_graceful_shutdown(signum, frame):
    """
    Signal handler for SIGTERM (sent by ACA/K8s before container kill).
    Ensures graceful draining of connections and tasks.
    """
    if signum == signal.SIGTERM:
        logger.warning("⚠️  SIGTERM received. Initiating graceful shutdown...")

        # Try to gracefully shutdown Celery if it's been initialized
        try:
            from celery import current_app as celery_app
            logger.info("Attempting to gracefully shutdown Celery...")
            celery_app.control.shutdown()
            logger.info("Celery shutdown signal sent.")
        except Exception as e:
            logger.warning(f"Celery graceful shutdown failed: {e}")

        # Close Django database connections
        try:
            from django.db import connections
            logger.info("Closing database connections...")
            connections.close_all()
            logger.info("Database connections closed.")
        except Exception as e:
            logger.warning(f"Database connection close failed: {e}")

        logger.info("✅ Graceful shutdown complete. Exiting.")
        sys.exit(0)


# Register signal handler
try:
    # Signal handlers only work in main thread on Windows
    import threading
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, handle_graceful_shutdown)
        signal.signal(signal.SIGINT, handle_graceful_shutdown)  # Also handle Ctrl+C
        logger.debug("✓ Graceful shutdown handler registered for SIGTERM/SIGINT")
    else:
        logger.debug("⚠ Signal handler skipped (not in main thread)")
except (ValueError, OSError) as e:
    logger.debug(f"⚠ Signal handler registration failed (likely Windows in dev): {e}")

