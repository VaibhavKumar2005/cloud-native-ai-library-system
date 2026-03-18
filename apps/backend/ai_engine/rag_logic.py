"""
VeriRag AI Engine - Complete Verification Logic
Implements the "Librarian" verification protocol with hallucination detection
and automatic failover to Groq/Llama-3.
"""

import os
import json
import logging
import re
import time
import hvac  # For HashiCorp Vault
from functools import lru_cache
from openai import AzureOpenAI, OpenAI
from prometheus_client import Counter, Histogram, Gauge
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from ai_engine.models import Document

# Azure Search - optional for local dev, required for cloud
try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import SearchIndex
    from azure.identity import DefaultAzureCredential
    AZURE_SEARCH_AVAILABLE = True
except ImportError:
    SearchClient = None
    SearchIndexClient = None
    SearchIndex = None
    DefaultAzureCredential = None
    AZURE_SEARCH_AVAILABLE = False
    logging.warning("Azure Search not available - vector search will be disabled")

# Import tracing utilities (graceful fallback if not configured)
try:
    from ai_engine.tracing import (
        trace_span,
        trace_context,
        add_span_attributes,
        record_event,
        get_trace_id,
    )
except ImportError:
    # Fallback no-op implementations
    def trace_span(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def trace_context(*args, **kwargs):
        from contextlib import nullcontext
        return nullcontext()
    def add_span_attributes(*args, **kwargs):
        pass
    def record_event(*args, **kwargs):
        pass
    def get_trace_id():
        return None

# Set up logging for debugging
logger = logging.getLogger(__name__)

# ============================================================================
# PROMETHEUS METRICS FOR MISSION CONTROL
# ============================================================================
VERIFICATION_REJECTIONS = Counter(
    'verirag_hallucination_rejections_total',
    'Total number of AI responses rejected for low faithfulness'
)

LLM_FALLBACKS = Counter(
    'verirag_llm_fallbacks_total',
    'Total number of times the system switched to the backup LLM'
)

QUERIES_TOTAL = Counter(
    'verirag_queries_total',
    'Total number of RAG queries processed'
)

DOCUMENTS_INGESTED = Counter(
    'verirag_documents_ingested_total',
    'Total number of documents successfully ingested'
)

FAITHFULNESS_HISTOGRAM = Histogram(
    'verirag_faithfulness_score',
    'Distribution of faithfulness scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

ACTIVE_MODEL = Gauge(
    'verirag_active_model',
    'Currently active LLM model (1=Gemini, 2=Groq)',
)
ACTIVE_MODEL.set(1)  # Default to Gemini

# ============================================================================
# CONFIGURATION
# ============================================================================
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "devpassword")
DB_HOST = os.environ.get("POSTGRES_HOST", "rag-db")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "verirag_db")

CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# AZURE CONFIGURATION
# ============================================================================
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4-turbo")

AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "verirag-documents")

# Verification thresholds
FAITHFULNESS_THRESHOLD = 0.6  # Below this triggers fallback
SIMILARITY_THRESHOLD = 0.7    # Minimum similarity score for context


def _build_evidence_payload(docs):
    evidence = []
    for i, doc in enumerate(docs, start=1):
        page = doc.metadata.get('page', 'Unknown')
        title = doc.metadata.get('document_title', 'Document')
        evidence.append(
            {
                "source_index": i,
                "document_title": title,
                "page": page,
                "chunk_index": doc.metadata.get("chunk_index"),
                "citation": f"{title} (Page {page})",
                "excerpt": doc.page_content[:320].strip(),
            }
        )
    return evidence


def _extract_unique_document_ids(docs):
    document_ids = []
    for doc in docs:
        document_id = doc.metadata.get("document_id")
        if document_id is not None:
            document_ids.append(str(document_id))
    return sorted(set(document_ids))

# ============================================================================
# DUAL-MODE SECRET RETRIEVAL
# ============================================================================
# Detects DEPLOY_MODE to choose HashiCorp Vault (local) or Azure Key Vault (cloud).
# API keys are NEVER stored in .env or environment variables.
# ============================================================================
_api_key_cache = {}  # Per-key cache: { "KEY_NAME": { "value": ..., "ts": ... } }
CACHE_TTL = 300  # 5 minutes

DEPLOY_MODE = os.environ.get('DEPLOY_MODE', 'local').lower()
AZURE_KEY_VAULT_URL = os.environ.get('AZURE_KEY_VAULT_URL')

# Override: if AZURE_KEY_VAULT_URL is set, treat as cloud
if AZURE_KEY_VAULT_URL:
    DEPLOY_MODE = 'cloud'


def _get_vault_client():
    """
    Creates and validates a HashiCorp Vault client connection (local mode only).
    Returns (client, error_message) tuple.
    """
    vault_url = os.environ.get('VAULT_ADDR', 'http://rag-vault:8200')
    vault_token = os.environ.get('VAULT_TOKEN')

    if not vault_token:
        return None, "VAULT_TOKEN not set"

    try:
        client = hvac.Client(url=vault_url, token=vault_token)
        if not client.is_authenticated():
            return None, "Vault authentication failed"
        return client, None
    except Exception as e:
        return None, str(e)


def get_api_key_from_vault(key_name="GOOGLE_API_KEY"):
    """
    Retrieves API keys from the active secret backend with per-key caching.

    Dual-mode:
      - DEPLOY_MODE=local  → HashiCorp Vault KV v2 at secret/myapp
      - DEPLOY_MODE=cloud  → Azure Key Vault (via DefaultAzureCredential)

    Falls back to environment variables ONLY if both vault backends fail.

    Expected keys: GOOGLE_API_KEY, GROQ_API_KEY
    """
    import time

    current_time = time.time()

    # Check per-key cache first
    cached = _api_key_cache.get(key_name)
    if cached and (current_time - cached["ts"]) < CACHE_TTL:
        return cached["value"]

    api_key = None

    if DEPLOY_MODE == 'cloud' and AZURE_KEY_VAULT_URL:
        # ── Azure Key Vault path ──
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            client = SecretClient(
                vault_url=AZURE_KEY_VAULT_URL,
                credential=DefaultAzureCredential(),
            )
            azure_secret_name = key_name.replace('_', '-')  # GOOGLE_API_KEY → GOOGLE-API-KEY
            api_key = client.get_secret(azure_secret_name).value
            if api_key:
                _api_key_cache[key_name] = {"value": api_key, "ts": current_time}
                logger.info(f"✅ Retrieved {key_name} from Azure Key Vault (cached for {CACHE_TTL}s)")
                return api_key
        except ImportError:
            logger.error("azure-identity or azure-keyvault-secrets not installed")
        except Exception as e:
            logger.error(f"Azure Key Vault error for {key_name}: {e}")
    else:
        # ── HashiCorp Vault path (local mode) ──
        try:
            client, err = _get_vault_client()
            if client is None:
                logger.warning(f"Vault unavailable ({err}), falling back to env for {key_name}")
                return os.environ.get(key_name)

            secret_response = client.secrets.kv.v2.read_secret_version(
                path='myapp',
                mount_point='secret'
            )

            api_key = secret_response['data']['data'].get(key_name)

            if api_key:
                _api_key_cache[key_name] = {"value": api_key, "ts": current_time}
                logger.info(f"✅ Retrieved {key_name} from Vault (cached for {CACHE_TTL}s)")
                return api_key

        except hvac.exceptions.VaultError as ve:
            logger.error(f"Vault API error for {key_name}: {ve}")
        except Exception as e:
            logger.error(f"Vault connection error for {key_name}: {e}")

    logger.warning(f"{key_name} not found in vault, falling back to environment")
    return os.environ.get(key_name)


def get_groq_api_key():
    """Retrieves Groq API key from Vault or environment."""
    return get_api_key_from_vault("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Creates Azure OpenAI embedding model.
    Uses Azure Key Vault or environment variables for credentials.
    Cached at module level to avoid recreating connection on every request.
    """
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
        raise ValueError("Azure OpenAI credentials not configured (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY)")
    
    return AzureOpenAIEmbeddings(
        model="text-embedding-3-small",
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY
    )


@lru_cache(maxsize=1)
def get_vector_store():
    """
    Gets configured Azure AI Search client.
    Cached at module level to reuse connection.
    """
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        raise ValueError("Azure AI Search credentials not configured")
    
    # Use Key-based authentication for simplicity
    # For production, consider using DefaultAzureCredential
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=AZURE_SEARCH_KEY
    )
    return search_client


# ============================================================================
# 1. THE INGESTION ENGINE - PDF Processing Pipeline
# ============================================================================
def ingest_document(doc_id):
    """
    Takes a Document ID and processes the PDF into vector embeddings.
    Uses LangChain's RecursiveCharacterTextSplitter for optimal chunking.
    Processes in batches to respect API rate limits (free-tier: 100 req/min).
    """
    import time as _time

    # Demo-friendly defaults: faster indexing while still allowing runtime tuning.
    BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "32"))
    BATCH_DELAY = float(os.environ.get("EMBEDDING_BATCH_DELAY_SECONDS", "1.5"))

    try:
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        logger.info(f"📄 Starting ingestion for: {doc.title}")
        doc.processed = False
        doc.status = Document.Status.INDEXING
        doc.progress_percent = 0
        doc.total_chunks = 0
        doc.processed_chunks = 0
        doc.last_error = ''
        doc.save(update_fields=[
            'processed',
            'status',
            'progress_percent',
            'total_chunks',
            'processed_chunks',
            'last_error',
        ])

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        # Step 1: Safe PDF text extraction
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        
        if not raw_docs:
            raise ValueError("PDF extraction returned no content")
        
        logger.info(f"📖 Extracted {len(raw_docs)} pages from PDF")

        # Step 2: Intelligent text chunking with overlap for context preservation
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(raw_docs)
        
        logger.info(f"✂️ Split into {len(chunks)} chunks")
        doc.total_chunks = len(chunks)
        doc.save(update_fields=['total_chunks'])

        # Step 3: Enrich metadata for multi-tenant isolation
        for i, chunk in enumerate(chunks):
            chunk.metadata["user_id"] = str(doc.user.id) if doc.user else "public"
            chunk.metadata["document_id"] = str(doc.id)
            chunk.metadata["document_title"] = doc.title
            chunk.metadata["chunk_index"] = i

        # Step 4: Generate embeddings and store in PGVector (batched for rate limits)
        embedding_model = get_embedding_model()
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(chunks))
            batch = chunks[start:end]
            
            logger.info(f"📦 Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} chunks)")
            
            # Retry logic for rate limit errors
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    PGVector.from_documents(
                        embedding=embedding_model,
                        documents=batch,
                        collection_name=COLLECTION_NAME,
                        connection_string=CONNECTION_STRING,
                        pre_delete_collection=False
                    )
                    processed_chunks = min(end, len(chunks))
                    progress_percent = int((processed_chunks / len(chunks)) * 100) if chunks else 100
                    doc.processed_chunks = processed_chunks
                    doc.progress_percent = progress_percent
                    doc.save(update_fields=['processed_chunks', 'progress_percent'])
                    break  # Success
                except Exception as e:
                    if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                        wait_time = max(BATCH_DELAY, 1.0) * (attempt + 1)
                        logger.warning(f"⏳ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        _time.sleep(wait_time)
                    else:
                        raise  # Non-rate-limit error, propagate
            
            # Pause between batches (skip after last batch)
            if batch_idx < total_batches - 1 and BATCH_DELAY > 0:
                logger.info(f"⏳ Rate limit pause ({BATCH_DELAY}s) before next batch...")
                _time.sleep(BATCH_DELAY)

        # Step 5: Update document status
        doc.processed = True
        doc.status = Document.Status.INDEXED
        doc.progress_percent = 100
        doc.processed_chunks = len(chunks)
        doc.last_error = ''
        doc.save(update_fields=[
            'processed',
            'status',
            'progress_percent',
            'processed_chunks',
            'last_error',
        ])
        
        # Increment Prometheus metric
        DOCUMENTS_INGESTED.inc()
        
        logger.info(f"✅ Document '{doc.title}' indexed successfully with {len(chunks)} vectors")
        return {
            "status": "success",
            "document_id": doc.id,
            "chunks_created": len(chunks),
            "message": f"Indexed {len(chunks)} chunks from '{doc.title}'"
        }

    except Document.DoesNotExist:
        logger.error(f"❌ Document with ID {doc_id} not found")
        return {"status": "error", "message": f"Document {doc_id} not found"}
    except Exception as e:
        logger.error(f"❌ Ingestion failed for doc {doc_id}: {str(e)}")
        Document.objects.filter(id=doc_id).update(
            processed=False,
            status=Document.Status.FAILED,
            last_error=str(e),
        )
        return {"status": "error", "message": str(e)}


def process_pdf_to_vector_db(file_path, user_id=None):
    """
    Standalone function to process a PDF file directly without Django model.
    Useful for testing and CLI operations.
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(raw_docs)
        
        for i, chunk in enumerate(chunks):
            chunk.metadata["user_id"] = str(user_id) if user_id else "public"
            chunk.metadata["source_file"] = os.path.basename(file_path)
            chunk.metadata["chunk_index"] = i
        
        PGVector.from_documents(
            embedding=get_embedding_model(),
            documents=chunks,
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            pre_delete_collection=False
        )
        
        DOCUMENTS_INGESTED.inc()
        return {"status": "success", "chunks": len(chunks)}
        
    except Exception as e:
        logger.error(f"❌ PDF processing failed: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# 2. LLM ROUTER WITH AUTOMATIC FAILOVER
# ============================================================================
def call_gemini(prompt, _retries=2):
    """
    Primary LLM: Azure OpenAI GPT-4 with JSON mode. Retries on rate limits.
    """
    with trace_context(
        "rag.provider.azure_openai.generate",
        {
            "gen_ai.system": "azure_openai",
            "gen_ai.request.model": AZURE_OPENAI_MODEL,
            "rag.provider": "azure_openai",
            "rag.provider.max_retries": _retries,
        },
    ):
        if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
            raise ValueError("Azure OpenAI credentials not configured")

        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        for attempt in range(_retries + 1):
            try:
                add_span_attributes({"rag.provider.attempt": attempt + 1})
                
                response = client.chat.completions.create(
                    model=AZURE_OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are VeriRag, a strictly faithful AI Librarian. Always output valid JSON with the exact schema requested."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temperature for factual responses
                    response_format={"type": "json_object"}
                )
                
                record_event(
                    "rag.provider.success",
                    {"rag.provider": "azure_openai", "rag.provider.attempt": attempt + 1},
                )
                return response.choices[0].message.content
                
            except Exception as e:
                record_event(
                    "rag.provider.error",
                    {
                        "rag.provider": "azure_openai",
                        "rag.provider.attempt": attempt + 1,
                        "error.message": str(e),
                    },
                )
                if ('429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e)) and attempt < _retries:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⏳ Azure OpenAI rate limited — retrying in {wait}s (attempt {attempt+1}/{_retries})")
                    time.sleep(wait)
                else:
                    raise


def call_groq_llama(prompt):
    """Backup LLM: Groq's Llama-3 for failover."""
    with trace_context(
        "rag.provider.groq.generate",
        {
            "gen_ai.system": "groq",
            "gen_ai.request.model": "llama-3.3-70b-versatile",
            "rag.provider": "groq",
        },
    ):
        groq_key = get_groq_api_key()
        if not groq_key:
            raise ValueError("GROQ_API_KEY not available in Vault or environment")

        client = OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are VeriRag, a strictly faithful AI Librarian. Always output valid JSON with the exact schema requested."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        record_event("rag.provider.success", {"rag.provider": "groq"})
        return response.choices[0].message.content


def call_llm_with_fallback(prompt):
    """
    Intelligent LLM router: Tries Azure OpenAI first, automatically fails over to Groq.
    Updates Prometheus metrics on failover.
    Azure OpenAI uses AZURE_OPENAI_KEY, Groq uses GROQ_API_KEY from Vault.
    """
    with trace_context("rag.provider.router", {"rag.provider.primary": "azure_openai"}):
        try:
            ACTIVE_MODEL.set(1)  # Azure OpenAI
            response = call_gemini(prompt)
            add_span_attributes({"rag.provider.selected": "azure_openai"})
            return response, "azure_openai"

        except Exception as primary_error:
            LLM_FALLBACKS.inc()
            ACTIVE_MODEL.set(2)  # Groq
            add_span_attributes(
                {
                    "rag.provider.selected": "groq",
                    "rag.provider.fallback_used": True,
                }
            )
            record_event(
                "rag.provider.failover",
                {
                    "rag.provider.from": "azure_openai",
                    "rag.provider.to": "groq",
                    "error.message": str(primary_error),
                },
            )
            logger.warning(f"⚠️ Azure OpenAI failed: {primary_error}. Switching to Groq/Llama-3...")

            try:
                response = call_groq_llama(prompt)
                return response, "groq"

            except Exception as backup_error:
                logger.error(f"❌ Both LLMs failed. Azure OpenAI: {primary_error}, Groq: {backup_error}")
                record_event(
                    "rag.provider.unavailable",
                    {
                        "rag.provider.primary_error": str(primary_error),
                        "rag.provider.backup_error": str(backup_error),
                    },
                )
                return json.dumps({
                    "answer": "System Notice: All AI providers are currently unavailable. Please try again later.",
                    "faithfulness_score": 0.0,
                    "explanation": "Both primary (Azure OpenAI) and backup (Groq) LLMs failed.",
                    "source_citation": "System Error",
                    "verification_passed": False
                }), "error"


# ============================================================================
# 3. THE VERIFICATION ENGINE - Core "Librarian" Protocol
# ============================================================================
def verify_faithfulness(answer, context, query):
    """
    Semantic faithfulness verification using embedding cosine similarity.
    Replaces naive word-overlap heuristics with embedding-based comparison.
    
    Returns a faithfulness score (0.0-1.0) and verification explanation.
    This detects subtle hallucinations better than word tally.
    """
    with trace_context(
        "rag.verification.semantic",
        {
            "rag.query.length": len(query or ""),
            "rag.answer.length": len(answer or ""),
            "rag.context.length": len(context or ""),
        },
    ):
        if not answer or not context:
            add_span_attributes({"rag.verification.score": 0.5})
            return 0.5, "Answer or context is empty"
        
        try:
            # Get embeddings for answer and context using the same model
            embedding_model = get_embedding_model()
            answer_embedding = embedding_model.embed_query(answer)
            context_embedding = embedding_model.embed_query(context)
            
            # Compute cosine similarity between answer and context embeddings
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            similarity_matrix = cosine_similarity(
                [answer_embedding], 
                [context_embedding]
            )
            similarity_score = float(similarity_matrix[0][0])
            
            # Normalize to 0-1 range (cosine similarity is already -1 to 1, but for embeddings typically 0-1)
            final_score = max(0.0, min(1.0, similarity_score))
            
            add_span_attributes(
                {
                    "rag.verification.score": round(final_score, 4),
                    "rag.verification.method": "semantic_cosine_similarity",
                }
            )
            explanation = f"Semantic similarity: {final_score:.2%}"
            return final_score, explanation
            
        except Exception as e:
            logger.error(f"Semantic verification failed, falling back to heuristic: {e}")
            # Fallback to simple word overlap if embeddings fail
            answer_lower = answer.lower()
            context_lower = context.lower()
            
            answer_words = set(re.findall(r'\b\w{4,}\b', answer_lower))
            context_words = set(re.findall(r'\b\w{4,}\b', context_lower))
            
            if not answer_words:
                return 0.5, "Unable to extract key terms from answer"
            
            overlap = answer_words.intersection(context_words)
            coverage = len(overlap) / len(answer_words) if answer_words else 0
            new_terms = answer_words - context_words
            novelty_penalty = min(len(new_terms) * 0.05, 0.3)
            base_score = coverage - novelty_penalty
            final_score = max(0.0, min(1.0, base_score + 0.3))
            
            add_span_attributes({"rag.verification.score": final_score})
            return final_score, f"Fallback heuristic - overlap: {len(overlap)}/{len(answer_words)}"


def evaluate_with_ragas(query: str, answer: str, contexts: list, ground_truth: str = None) -> dict:
    """
    LLM-based evaluation using RAGAS framework.
    Replaces heuristic verification with four proper metrics using LLM judgment.
    
    Returns dict with:
      - faithfulness: Is the answer grounded in the context? (0-1)
      - answer_relevancy: Does the answer actually address the question? (0-1)
      - context_precision: Are the retrieved chunks relevant? (0-1)
      - context_recall: Did we retrieve enough to answer? (0-1, requires ground_truth)
      - combined_score: Weighted aggregate score (0-1)
    
    All metrics use the same Gemini model as the main pipeline to ensure consistency.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
        
        # Prepare data in RAGAS format
        # contexts should be list of text strings from retrieved documents
        if isinstance(contexts, list) and len(contexts) > 0:
            if hasattr(contexts[0], 'page_content'):
                # LangChain Document objects
                context_texts = [doc.page_content for doc in contexts]
            else:
                # Plain strings
                context_texts = contexts
        else:
            context_texts = []
        
        data_dict = {
            "question": [query],
            "answer": [answer],
            "contexts": [context_texts],
        }
        
        # Include ground truth if provided for context recall calculation
        metrics_to_evaluate = [faithfulness, answer_relevancy, context_precision]
        if ground_truth:
            data_dict["ground_truth"] = [ground_truth]
            metrics_to_evaluate.append(context_recall)
        
        # Create RAGAS dataset and evaluate
        dataset = Dataset.from_dict(data_dict)
        result = evaluate(dataset, metrics=metrics_to_evaluate)
        
        # Extract scores with safe defaults
        ragas_scores = {
            "faithfulness": round(float(result.get("faithfulness", 0.5)), 3),
            "answer_relevancy": round(float(result.get("answer_relevancy", 0.5)), 3),
            "context_precision": round(float(result.get("context_precision", 0.5)), 3),
            "context_recall": round(float(result.get("context_recall", 0.0)), 3) if ground_truth else 0.0,
        }
        
        # Calculate weighted combined score
        # Faithfulness: 50% (most critical - must be grounded)
        # Answer relevancy: 30% (must address the question)
        # Context precision: 20% (retrieval quality matters)
        ragas_scores["combined_score"] = round(
            (ragas_scores["faithfulness"] * 0.5) +
            (ragas_scores["answer_relevancy"] * 0.3) +
            (ragas_scores["context_precision"] * 0.2),
            3
        )
        
        # Log metrics to Prometheus
        FAITHFULNESS_HISTOGRAM.observe(ragas_scores["faithfulness"])
        
        # Attach all scores to trace span
        add_span_attributes({
            "rag.ragas.faithfulness": ragas_scores["faithfulness"],
            "rag.ragas.answer_relevancy": ragas_scores["answer_relevancy"],
            "rag.ragas.context_precision": ragas_scores["context_precision"],
            "rag.ragas.context_recall": ragas_scores["context_recall"],
            "rag.ragas.combined_score": ragas_scores["combined_score"],
        })
        
        logger.info(f"RAGAS evaluation complete - faithfulness: {ragas_scores['faithfulness']:.2f}")
        return ragas_scores
        
    except ImportError as e:
        logger.warning(f"RAGAS not available ({e}), falling back to basic verification")
        # Fallback: use existing semantic verification
        score, explanation = verify_faithfulness(answer, "\n".join(
            [c.page_content if hasattr(c, 'page_content') else str(c) for c in contexts]
        ), query)
        return {
            "faithfulness": score,
            "answer_relevancy": 0.5,
            "context_precision": 0.5,
            "context_recall": 0.0,
            "combined_score": score,
        }
    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        # Safe fallback
        return {
            "faithfulness": 0.5,
            "answer_relevancy": 0.5,
            "context_precision": 0.5,
            "context_recall": 0.0,
            "combined_score": 0.5,
        }


def get_verified_answer(query, user_id, request_context=None):
    """
    The complete VeriRag verification pipeline:
    1. Similarity search in PGVector
    2. Generate response using Gemini
    3. Verify faithfulness against raw context
    4. If faithfulness < threshold, regenerate with Groq/Llama-3
    5. Return standardized JSON with integrity metrics
    """
    QUERIES_TOTAL.inc()
    request_context = request_context or {}
    query_id = request_context.get("query_id")

    with trace_context(
        "rag.query.pipeline",
        {
            "enduser.id": user_id,
            "rag.query.id": query_id,
            "rag.query.length": len(query or ""),
            "rag.trace.parent": request_context.get("trace_id"),
        },
    ):
        add_span_attributes(
            {
                "rag.query.id": query_id,
                "rag.trace_id": get_trace_id() or "",
            }
        )
        record_event("rag.query.pipeline.started", {"rag.query.id": query_id})

        try:
            with trace_context(
                "rag.retrieval.vector_search",
                {
                    "db.system": "postgresql",
                    "rag.retrieval.top_k": 5,
                    "enduser.id": user_id,
                },
            ):
                # Use cached vector store to reuse connection pool
                vector_db = get_vector_store()

                docs = vector_db.similarity_search(
                    query,
                    k=5,
                    filter={"user_id": str(user_id)}
                )
                add_span_attributes(
                    {
                        "rag.retrieval.result_count": len(docs),
                        "rag.retrieval.document_ids": ",".join(_extract_unique_document_ids(docs)),
                    }
                )
                record_event(
                    "rag.retrieval.completed",
                    {"rag.retrieval.result_count": len(docs)},
                )

            if not docs:
                return {
                    "answer": "I couldn't find any relevant information in your uploaded documents. Please upload a document first or rephrase your question.",
                    "faithfulness_score": 0.0,
                    "explanation": "No matching vectors found for this user's document collection.",
                    "source_citation": "None",
                    "evidence_items": [],
                    "verification_passed": True,
                    "model_used": "none",
                    "context_chunks_used": 0,
                    "evaluation": {
                        "faithfulness": 0.0,
                        "answer_relevancy": 0.0,
                        "context_precision": 0.0,
                        "context_recall": 0.0,
                        "combined_score": 0.0,
                    }
                }

            context_parts = []
            citations = []
            evidence_items = _build_evidence_payload(docs)
            for i, doc in enumerate(docs):
                page = doc.metadata.get('page', 'Unknown')
                title = doc.metadata.get('document_title', 'Document')
                context_parts.append(f"[Source {i+1}: {title}, Page {page}]\n{doc.page_content}")
                citations.append(f"{title} (Page {page})")

            context = "\n\n---\n\n".join(context_parts)
            source_citation = "; ".join(set(citations))

            generation_prompt = f"""You are VeriRag, a strictly faithful AI Librarian. Your ONLY job is to answer questions using ONLY the provided context.

STRICT RULES:
1. ONLY use information explicitly stated in the context below
2. If the context doesn't contain the answer, say "The provided documents don't contain information about this."
3. NEVER make up facts, dates, names, or statistics not in the context
4. Quote directly from the context when possible
5. Be concise but complete

CONTEXT FROM USER'S DOCUMENTS:
{context}

USER QUESTION: {query}

Respond with this exact JSON structure:
{{
    "answer": "Your factual answer based only on the context above",
    "faithfulness_score": <float between 0.0 and 1.0 - how confident are you that this answer is 100% from the context>,
    "explanation": "Brief explanation of where in the context this answer comes from",
    "source_citation": "Direct quote or specific page reference from the context"
}}"""

            with trace_context(
                "rag.generation.response",
                {
                    "rag.context.chunk_count": len(docs),
                    "rag.prompt.length": len(generation_prompt),
                },
            ):
                response_text, model_used = call_llm_with_fallback(generation_prompt)
                add_span_attributes({"rag.response.model_used": model_used})

            try:
                with trace_context("rag.response.parse", {"rag.response.model_used": model_used}):
                    clean_json = response_text.strip()
                    if clean_json.startswith('```'):
                        clean_json = re.sub(r'^```(?:json)?\s*', '', clean_json)
                        clean_json = re.sub(r'\s*```$', '', clean_json)
                    response_data = json.loads(clean_json)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}. Raw response: {response_text[:500]}")
                return {
                    "answer": "Error parsing AI response. Please try again.",
                    "faithfulness_score": 0.0,
                    "explanation": f"JSON decode error: {str(e)}",
                    "source_citation": source_citation,
                    "evidence_items": evidence_items,
                    "verification_passed": False,
                    "model_used": model_used,
                    "context_chunks_used": len(docs),
                    "evaluation": {
                        "faithfulness": 0.0,
                        "answer_relevancy": 0.0,
                        "context_precision": 0.0,
                        "context_recall": 0.0,
                        "combined_score": 0.0,
                    }
                }

            answer = response_data.get("answer", "")
            initial_score = float(response_data.get("faithfulness_score", 0.0) or 0.0)
            verification_score, verification_explanation = verify_faithfulness(answer, context, query)

            combined_score = (initial_score * 0.6) + (verification_score * 0.4)
            FAITHFULNESS_HISTOGRAM.observe(combined_score)
            verification_passed = combined_score >= FAITHFULNESS_THRESHOLD
            add_span_attributes(
                {
                    "rag.response.initial_faithfulness_score": initial_score,
                    "rag.verification.score": round(verification_score, 4),
                    "rag.response.combined_faithfulness_score": round(combined_score, 4),
                    "rag.response.verification_passed": verification_passed,
                }
            )

            if not verification_passed:
                VERIFICATION_REJECTIONS.inc()
                logger.warning(f"⚠️ Low faithfulness detected ({combined_score:.2f}). Triggering verification protocol...")
                record_event(
                    "rag.verification.failed",
                    {
                        "rag.response.combined_faithfulness_score": round(combined_score, 4),
                        "rag.response.model_used": model_used,
                    },
                )

                strict_prompt = f"""CRITICAL: Previous response failed verification. Generate a MORE CONSERVATIVE answer.

CONTEXT:
{context}

QUESTION: {query}

RULES:
- If unsure, say "Based on the available documents, I cannot definitively answer this question."
- Only state facts that are DIRECTLY quoted in the context
- Provide the EXACT quote from the context that supports your answer

JSON Response:
{{
    "answer": "Conservative, fact-checked answer",
    "faithfulness_score": <float 0.0-1.0>,
    "explanation": "Verification explanation",
    "source_citation": "Direct quote from context"
}}"""

                try:
                    with trace_context("rag.verification.regeneration", {"rag.provider": "groq"}):
                        strict_response = call_groq_llama(strict_prompt)
                        strict_data = json.loads(strict_response)
                        response_data = strict_data
                        model_used = "groq_verification"
                        LLM_FALLBACKS.inc()
                except Exception as e:
                    logger.error(f"Strict regeneration failed: {e}")
                    response_data["explanation"] = f"⚠️ Low confidence ({combined_score:.2f}): {response_data.get('explanation', '')}"

            with trace_context(
                "rag.response.build",
                {
                    "rag.response.model_used": model_used,
                    "rag.context.chunk_count": len(docs),
                },
            ):
                # Evaluate with RAGAS for LLM-based quality metrics
                answer = response_data.get("answer", "Unable to generate response")
                ragas_scores = evaluate_with_ragas(
                    query=query,
                    answer=answer,
                    contexts=docs,
                    ground_truth=None
                )
                
                # Build response with both legacy and RAGAS metrics
                final_response = {
                    "answer": answer,
                    "faithfulness_score": round(combined_score, 2),
                    "explanation": response_data.get("explanation", verification_explanation),
                    "source_citation": response_data.get("source_citation", source_citation),
                    "evidence_items": evidence_items,
                    "verification_passed": verification_passed,
                    "model_used": model_used,
                    "context_chunks_used": len(docs),
                    # RAGAS evaluation metrics (LLM-based quality judgment)
                    "evaluation": {
                        "faithfulness": ragas_scores.get("faithfulness", 0.5),
                        "answer_relevancy": ragas_scores.get("answer_relevancy", 0.5),
                        "context_precision": ragas_scores.get("context_precision", 0.5),
                        "context_recall": ragas_scores.get("context_recall", 0.0),
                        "combined_score": ragas_scores.get("combined_score", 0.5),
                    }
                }
                record_event(
                    "rag.response.ready",
                    {
                        "rag.response.model_used": model_used,
                        "rag.context.chunk_count": len(docs),
                        "rag.response.verification_passed": verification_passed,
                        "rag.evaluation.faithfulness": ragas_scores.get("faithfulness", 0.5),
                    },
                )
                return final_response

        except Exception as e:
            logger.error(f"❌ Verification engine error: {str(e)}")
            return {
                "answer": "An internal error occurred while processing your question.",
                "faithfulness_score": 0.0,
                "explanation": str(e),
                "source_citation": "System Error",
                "evidence_items": [],
                "verification_passed": False,
                "model_used": "none",
                "context_chunks_used": 0,
                "evaluation": {
                    "faithfulness": 0.0,
                    "answer_relevancy": 0.0,
                    "context_precision": 0.0,
                    "context_recall": 0.0,
                    "combined_score": 0.0,
                }
            }
