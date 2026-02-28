"""
VeriRAG OpenTelemetry Tracing Integration
Provides distributed tracing across the RAG pipeline for observability.
"""

import os
import logging
import functools
from contextlib import contextmanager
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

OTEL_ENABLED = os.environ.get('OTEL_ENABLED', 'true').lower() == 'true'
OTEL_SERVICE_NAME = os.environ.get('OTEL_SERVICE_NAME', 'verirag-backend')
OTEL_EXPORTER_ENDPOINT = os.environ.get('OTEL_EXPORTER_ENDPOINT', 'http://localhost:4317')

_tracer = None
_initialized = False


def _init_tracing():
    """Initialize OpenTelemetry tracing if available."""
    global _tracer, _initialized
    
    if _initialized:
        return _tracer
    
    _initialized = True
    
    if not OTEL_ENABLED:
        logger.info("OpenTelemetry tracing disabled")
        return None
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.semconv.resource import ResourceAttributes
        
        # Try to import OTLP exporter
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_ENDPOINT)
            logger.info(f"OpenTelemetry OTLP exporter configured: {OTEL_EXPORTER_ENDPOINT}")
        except ImportError:
            # Fall back to console exporter
            exporter = ConsoleSpanExporter()
            logger.info("OpenTelemetry using console exporter (OTLP not available)")
        
        # Create resource with service info
        resource = Resource(attributes={
            ResourceAttributes.SERVICE_NAME: OTEL_SERVICE_NAME,
            ResourceAttributes.SERVICE_VERSION: "2.0.0",
            "environment": os.environ.get('ENVIRONMENT', 'development')
        })
        
        # Set up tracer provider
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        _tracer = trace.get_tracer(OTEL_SERVICE_NAME)
        logger.info(f"✅ OpenTelemetry tracing initialized for {OTEL_SERVICE_NAME}")
        return _tracer
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry not installed: {e}. Tracing disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return None


def get_tracer():
    """Get the OpenTelemetry tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = _init_tracing()
    return _tracer


# ============================================================================
# TRACING DECORATORS
# ============================================================================

def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to create a trace span around a function.
    
    Usage:
        @trace_span("document_ingestion", {"operation": "pdf_processing"})
        def process_document(doc_id):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            if tracer is None:
                return func(*args, **kwargs)
            
            with tracer.start_as_current_span(span_name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                # Add function arguments as attributes
                if args:
                    span.set_attribute("args_count", len(args))
                if kwargs:
                    span.set_attribute("kwargs_keys", ",".join(kwargs.keys()))
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


@contextmanager
def trace_context(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for creating trace spans.
    
    Usage:
        with trace_context("vector_search", {"query_length": len(query)}):
            results = vector_db.similarity_search(query)
    """
    tracer = get_tracer()
    
    if tracer is None:
        yield None
        return
    
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
            span.set_attribute("status", "success")
        except Exception as e:
            span.set_attribute("status", "error")
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise


def add_span_attributes(attributes: Dict[str, Any]):
    """Add attributes to the current active span."""
    tracer = get_tracer()
    if tracer is None:
        return
    
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            for key, value in attributes.items():
                current_span.set_attribute(key, str(value))
    except Exception as e:
        logger.debug(f"Failed to add span attributes: {e}")


def record_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Record an event in the current span."""
    tracer = get_tracer()
    if tracer is None:
        return
    
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes=attributes or {})
    except Exception as e:
        logger.debug(f"Failed to record event: {e}")


# ============================================================================
# RAG PIPELINE SPECIFIC SPANS
# ============================================================================

@trace_span("rag.document_ingestion")
def trace_document_ingestion(func):
    """Specialized span for document ingestion."""
    return func


@trace_span("rag.embedding_generation")
def trace_embedding_generation(func):
    """Specialized span for embedding generation."""
    return func


@trace_span("rag.vector_search")  
def trace_vector_search(func):
    """Specialized span for vector similarity search."""
    return func


@trace_span("rag.llm_generation")
def trace_llm_generation(func):
    """Specialized span for LLM response generation."""
    return func


@trace_span("rag.verification")
def trace_verification(func):
    """Specialized span for faithfulness verification."""
    return func


# ============================================================================
# DJANGO MIDDLEWARE FOR REQUEST TRACING
# ============================================================================

class OpenTelemetryMiddleware:
    """
    Django middleware for automatic request tracing.
    Add to settings.py MIDDLEWARE list.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        _init_tracing()
    
    def __call__(self, request):
        tracer = get_tracer()
        
        if tracer is None:
            return self.get_response(request)
        
        span_name = f"{request.method} {request.path}"
        
        with tracer.start_as_current_span(span_name) as span:
            # Add request attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.build_absolute_uri())
            span.set_attribute("http.path", request.path)
            span.set_attribute("http.user_agent", request.META.get('HTTP_USER_AGENT', 'unknown'))
            
            if request.user.is_authenticated:
                span.set_attribute("user.id", request.user.id)
            
            try:
                response = self.get_response(request)
                span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code >= 400:
                    span.set_attribute("error", True)
                
                return response
                
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_trace_id() -> Optional[str]:
    """Get the current trace ID for correlation."""
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context.is_valid:
                return format(span_context.trace_id, '032x')
    except Exception:
        pass
    return None


def get_span_id() -> Optional[str]:
    """Get the current span ID for correlation."""
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context.is_valid:
                return format(span_context.span_id, '016x')
    except Exception:
        pass
    return None
