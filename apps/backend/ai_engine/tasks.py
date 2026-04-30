"""
VeriRAG Celery Tasks
Background tasks for automated document ingestion and system maintenance.
"""

import os
import logging
from datetime import datetime, timedelta
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# DOCUMENT INGESTION TASKS
# ============================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def ingest_document_task(self, document_id: int):
    """
    Celery task to ingest a single document asynchronously.
    
    Args:
        document_id: ID of the Document model instance
        
    Returns:
        dict with ingestion status and details
    """
    from ai_engine.models import Document
    from ai_engine.rag_logic import ingest_document
    
    logger.info(f"📄 [Task {self.request.id}] Starting ingestion for document {document_id}")
    
    try:
        # Check if document exists
        document = Document.objects.get(id=document_id)
        
        if document.processed and document.status == Document.Status.INDEXED:
            logger.info(f"Document {document_id} already processed, skipping")
            return {
                'status': 'skipped',
                'document_id': document_id,
                'reason': 'already_processed'
            }

        document.processed = False
        document.status = Document.Status.INDEXING
        document.progress_percent = 0
        document.processed_chunks = 0
        document.last_error = ''
        document.save(update_fields=[
            'processed',
            'status',
            'progress_percent',
            'processed_chunks',
            'last_error',
        ])
        
        # Run ingestion
        result = ingest_document(document_id)
        
        if result.get('status') == 'success':
            logger.info(f"✅ [Task {self.request.id}] Successfully ingested document {document_id}")
        else:
            logger.warning(f"⚠️ [Task {self.request.id}] Ingestion issues for document {document_id}: {result.get('message')}")
        
        return result
        
    except Document.DoesNotExist:
        logger.error(f"❌ Document {document_id} not found")
        return {
            'status': 'error',
            'document_id': document_id,
            'error': 'Document not found'
        }
        
    except Exception as e:
        logger.error(f"❌ [Task {self.request.id}] Ingestion failed for document {document_id}: {e}")

        Document.objects.filter(id=document_id).update(
            processed=False,
            status=Document.Status.FAILED,
            last_error=str(e),
        )
        
        # Check if we should retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            'status': 'error',
            'document_id': document_id,
            'error': str(e)
        }


@shared_task(bind=True)
def process_pending_documents(self):
    """
    Scheduled task to process all unprocessed documents.
    Runs every 5 minutes via Celery Beat.
    """
    from ai_engine.models import Document
    
    logger.info(f"🔄 [Scheduled Task] Checking for pending documents...")
    
    # Find all unprocessed documents
    pending_docs = Document.objects.exclude(status=Document.Status.INDEXED)
    count = pending_docs.count()
    
    if count == 0:
        logger.info("No pending documents to process")
        return {'status': 'complete', 'processed': 0}
    
    logger.info(f"Found {count} pending documents, queuing for processing...")
    
    processed = 0
    failed = 0
    
    for doc in pending_docs[:10]:  # Process max 10 at a time
        try:
            # Queue individual ingestion task
            ingest_document_task.delay(doc.id)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to queue document {doc.id}: {e}")
            failed += 1
    
    return {
        'status': 'queued',
        'total_pending': count,
        'queued': processed,
        'failed': failed
    }


@shared_task(bind=True)
def batch_ingest_documents(self, document_ids: list):
    """
    Batch process multiple documents.
    
    Args:
        document_ids: List of document IDs to process
    """
    logger.info(f"📚 [Batch Task] Processing {len(document_ids)} documents")
    
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    for doc_id in document_ids:
        try:
            result = ingest_document_task.delay(doc_id)
            
            if result:
                results['success'].append(doc_id)
                
        except Exception as e:
            results['failed'].append({'id': doc_id, 'error': str(e)})
    
    logger.info(f"✅ Batch complete: {len(results['success'])} success, {len(results['failed'])} failed, {len(results['skipped'])} skipped")
    
    return results


# ============================================================================
# MONITORING & HEALTH TASKS
# ============================================================================

@shared_task(bind=True)
def system_health_check(self):
    """
    Periodic health check task.
    Verifies database, Vault, and vector store connectivity.
    """
    from django.db import connection
    import hvac
    
    health = {
        'timestamp': datetime.now().isoformat(),
        'database': 'unknown',
        'vault': 'unknown',
        'overall': 'degraded'
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['database'] = 'connected'
    except Exception as e:
        health['database'] = f'error: {str(e)}'
    
    # Check Vault
    try:
        vault_url = os.environ.get('VAULT_ADDR', 'http://vault:8200')
        client = hvac.Client(url=vault_url)
        if client.sys.is_initialized() and not client.sys.read_seal_status()['sealed']:
            health['vault'] = 'unsealed'
        else:
            health['vault'] = 'sealed_or_uninitialized'
    except Exception as e:
        health['vault'] = f'error: {str(e)}'
    
    # Determine overall health
    if health['database'] == 'connected' and health['vault'] == 'unsealed':
        health['overall'] = 'healthy'
    elif health['database'] == 'connected':
        health['overall'] = 'partial'
    
    logger.info(f"🏥 Health check: {health['overall']}")
    
    return health


@shared_task(bind=True)
def export_daily_metrics(self):
    """
    Export daily metrics for analytics and reporting.
    """
    from prometheus_client import REGISTRY
    from ai_engine.models import Document
    
    logger.info("📊 Exporting daily metrics...")
    
    metrics = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'documents': {
            'total': Document.objects.count(),
            'processed': Document.objects.filter(status=Document.Status.INDEXED).count(),
            'pending': Document.objects.exclude(status=Document.Status.INDEXED).count(),
        },
        'prometheus': {
            'hallucinations_prevented': REGISTRY.get_sample_value('verirag_hallucination_rejections_total') or 0,
            'llm_fallbacks': REGISTRY.get_sample_value('verirag_llm_fallbacks_total') or 0,
            'queries_total': REGISTRY.get_sample_value('verirag_queries_total') or 0,
            'documents_ingested': REGISTRY.get_sample_value('verirag_documents_ingested_total') or 0,
        }
    }
    
    # Save to file (in production, send to metrics store)
    metrics_file = f"/tmp/verirag_metrics_{metrics['date']}.json"
    
    try:
        import json
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"✅ Metrics exported to {metrics_file}")
    except Exception as e:
        logger.warning(f"Could not save metrics file: {e}")
    
    return metrics


# ============================================================================
# MAINTENANCE TASKS
# ============================================================================

@shared_task(bind=True)
def cleanup_orphaned_vectors(self):
    """
    Clean up vector embeddings for deleted documents.
    Runs weekly during low-traffic hours.
    """
    from ai_engine.models import Document
    from ai_engine.rag_logic import CONNECTION_STRING, COLLECTION_NAME
    
    logger.info("🧹 Starting orphaned vector cleanup...")
    
    # Get all valid document IDs
    valid_doc_ids = set(str(doc.id) for doc in Document.objects.all())
    
    # This would require direct PGVector table access
    # In production, implement actual cleanup logic here
    
    cleanup_result = {
        'timestamp': datetime.now().isoformat(),
        'valid_documents': len(valid_doc_ids),
        'vectors_cleaned': 0,  # Would be populated by actual cleanup
        'status': 'simulated'
    }
    
    logger.info(f"🧹 Cleanup complete: {cleanup_result}")
    
    return cleanup_result


@shared_task(bind=True)
def reindex_all_documents(self, user_id: int = None):
    """
    Force re-index all documents (or documents for a specific user).
    Used for schema migrations or embedding model updates.
    
    Args:
        user_id: Optional user ID to filter documents
    """
    from ai_engine.models import Document
    
    logger.info(f"🔄 Starting full reindex {'for user ' + str(user_id) if user_id else 'for all users'}...")
    
    queryset = Document.objects.all()
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # Reset processed flag
    with transaction.atomic():
        queryset.update(
            processed=False,
            status=Document.Status.QUEUED,
            progress_percent=0,
            total_chunks=0,
            processed_chunks=0,
            last_error='',
        )
    
    # Queue all for reprocessing
    doc_ids = list(queryset.values_list('id', flat=True))
    
    # Queue in batches
    batch_size = 10
    for i in range(0, len(doc_ids), batch_size):
        batch = doc_ids[i:i+batch_size]
        batch_ingest_documents.delay(batch)
    
    return {
        'status': 'queued',
        'total_documents': len(doc_ids),
        'batches': (len(doc_ids) + batch_size - 1) // batch_size
    }


# ============================================================================
# WEBHOOK/EVENT TASKS
# ============================================================================

@shared_task(bind=True)
def on_document_uploaded(self, document_id: int):
    """
    Event handler when a new document is uploaded.
    Triggers immediate ingestion with high priority.
    """
    logger.info(f"📥 New document uploaded (ID: {document_id}), triggering immediate ingestion")
    
    # Queue with high priority
    ingest_document_task.apply_async(
        args=[document_id],
        priority=0,  # Highest priority
        countdown=2  # Small delay to ensure DB transaction is committed
    )
    
    return {'status': 'triggered', 'document_id': document_id}


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def process_abstract_to_vector_db(self, document_id: int):
    """
    Celery task to index a document's abstract/content into pgvector.
    Lightweight alternative to PDF processing for external papers.
    
    Args:
        document_id: ID of the Document model instance
        
    Returns:
        dict with indexing status
    """
    from ai_engine.models import Document
    from ai_engine.vector_store import replace_document_chunks, sanitize_utf8_text
    
    logger.info(f"📚 [Task {self.request.id}] Indexing abstract for document {document_id}")
    
    try:
        doc = Document.objects.get(id=document_id)
        
        # Get content from abstract/content field
        content = sanitize_utf8_text(doc.content or '')
        if not content:
            logger.warning(f"No content to index for document {document_id}")
            doc.status = Document.Status.INDEXED
            doc.processed = True
            doc.save()
            return {'status': 'no_content', 'document_id': document_id}
        
        chunk_ids = replace_document_chunks(
            doc.id,
            [content],
            [{
                'document_id': str(doc.id),
                'document_title': sanitize_utf8_text(doc.title),
                'page': 0,
                'page_number': 0,
                'chunk_index': 0,
                'is_qa': False,
                'citation_keys': [],
                'user_id': str(doc.user_id or 0),
                'source': doc.source,
            }]
        )
        
        # Mark document as processed
        doc.status = Document.Status.INDEXED
        doc.processed = True
        doc.total_chunks = 1
        doc.processed_chunks = 1
        doc.save()
        
        logger.info(f"✅ Successfully indexed abstract for document {document_id} ({len(chunk_ids)} vector chunk)")
        
        return {
            'status': 'indexed',
            'document_id': document_id,
            'chunk_id': chunk_ids[0] if chunk_ids else None,
            'content_length': len(content)
        }
    
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'status': 'error', 'error': 'Document not found'}
    
    except Exception as e:
        logger.error(f"Abstract indexing failed for document {document_id}: {str(e)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=min(60, 30 * (2 ** self.request.retries)))
        else:
            # Mark as failed after max retries
            try:
                doc = Document.objects.get(id=document_id)
                doc.status = Document.Status.FAILED
                doc.last_error = str(e)
                doc.save()
            except:
                pass
            
            return {'status': 'failed', 'error': str(e)}
