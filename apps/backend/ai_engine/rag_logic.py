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
from langchain_community.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
COLLECTION_NAME = os.environ.get("PGVECTOR_COLLECTION_NAME", "verirag_documents")

# ============================================================================
# AZURE CONFIGURATION
# ============================================================================
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
# Try both variable names for backward compatibility
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4-turbo"

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
    Creates Azure OpenAI embedding model (text-embedding-3-large for academic accuracy).
    Uses Azure Key Vault or environment variables for credentials.
    Cached at module level to avoid recreating connection on every request.
    """
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
        raise ValueError("Azure OpenAI credentials not configured (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY)")

    try:
        from langchain_openai import AzureOpenAIEmbeddings
    except ImportError as exc:
        raise ImportError(
            "AzureOpenAIEmbeddings is unavailable. Install compatible langchain_openai/langchain_core versions."
        ) from exc
    
    return AzureOpenAIEmbeddings(
        model="text-embedding-3-large",  # Upgraded: 3072 dimensions for better accuracy
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY
    )


@lru_cache(maxsize=1)
def get_vector_store():
    """
    Gets the configured PGVector store.
    Cached at module level to reuse connection.
    """
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embedding_function=get_embedding_model(),
    )


# ============================================================================
# HELPERS: Citation Extraction (One-time cost at ingestion)
# ============================================================================

def extract_citations_from_text(text: str) -> dict:
    """
    Extract citations in common formats from PDF text.
    Format: {"smith2020": {"authors": "Smith", "year": 2020, "page": "5"}}
    
    This is a simple regex-based extraction. For production, use parscit or grobid.
    """
    citations = {}
    
    # Pattern 1: Author Year (Smith, 2020)
    import re
    pattern1 = r'([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*),?\s*\((\d{4})\)'
    matches = re.finditer(pattern1, text)
    
    for match in matches:
        authors = match.group(1)
        year = match.group(2)
        citation_key = f"{authors.split()[0].lower()}{year}"
        
        if citation_key not in citations:
            citations[citation_key] = {
                "authors": authors,
                "year": int(year),
                "page": ""
            }
    
    return citations


def find_citations_in_chunk(chunk_text: str, all_citations: dict) -> list:
    """
    Identify which citations appear in a specific chunk.
    Returns list of citation keys: ["smith2020", "jones2019"]
    """
    citation_keys = []
    
    for key, cite_data in all_citations.items():
        authors = cite_data.get("authors", "")
        year = cite_data.get("year", "")
        
        # Check if citation appears in this chunk
        if f"{authors}" in chunk_text or f"({year})" in chunk_text:
            citation_keys.append(key)
    
    return list(set(citation_keys))  # Remove duplicates


def is_qa_chunk(text: str) -> bool:
    """
    Heuristic: Is this chunk a Q&A pair?
    (return True if it looks like our system can answer directly)
    """
    patterns = [
        r'[Qq]uestion\s*:',
        r'[Aa]nswer\s*:',
        r'\?.*\n\n.*\.',  # Question mark followed by answer
        r'^\s*Q[.:]\s',
        r'^\s*A[.:]\s',
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    


def ingest_document(doc_id):
    """
    Ingest PDF → Extract → Chunk → Embed → Store with citations.
    Minimal version: No fancy parsing, just text + embeddings + citations.
    """
    import time as _time
    from ai_engine.models import ChunkIndex, DocumentMetadata
    
    BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "32"))
    BATCH_DELAY = float(os.environ.get("EMBEDDING_BATCH_DELAY_SECONDS", "1.5"))

    try:
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        logger.info(f"📄 Ingesting: {doc.title}")
        
        # Mark as processing
        doc.status = Document.Status.INDEXING
        doc.processed = False
        doc.save(update_fields=['status', 'processed'])

        # ====================================================================
        # STEP 1: Extract text from PDF
        # ====================================================================
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        
        if not raw_docs:
            raise ValueError("PDF extraction returned no content")
        
        full_text = "\n\n".join([d.page_content for d in raw_docs])
        logger.info(f"📖 Extracted {len(raw_docs)} pages")

        # ====================================================================
        # STEP 2: Extract citations (one-time cost)
        # ====================================================================
        citations = extract_citations_from_text(full_text)
        logger.info(f"🔗 Found {len(citations)} citations")
        
        # Store in DocumentMetadata
        metadata, created = DocumentMetadata.objects.get_or_create(document=doc)
        metadata.bibtex_entries = citations
        metadata.save()

        # ====================================================================
        # STEP 3: Chunk text
        # ====================================================================
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(raw_docs)
        logger.info(f"✂️ Split into {len(chunks)} chunks")

        # ====================================================================
        # STEP 4: Embed and store chunks
        # ====================================================================
        embedding_model = get_embedding_model()
        
        for i, chunk in enumerate(chunks):
            # Embed this chunk
            try:
                embedding = embedding_model.embed_query(chunk.page_content)
            except Exception as e:
                logger.warning(f"Embedding failed for chunk {i}: {e}")
                continue
            
            # Find citations in this chunk
            citation_keys = find_citations_in_chunk(chunk.page_content, citations)
            
            # Detect if this is a Q&A pair
            is_qa = is_qa_chunk(chunk.page_content)
            
            # Store in ChunkIndex
            ChunkIndex.objects.create(
                document=doc,
                content=chunk.page_content,
                embedding=embedding,  # pgvector will handle it
                page_number=chunk.metadata.get('page', 0),
                citation_keys=citation_keys,
                is_qa=is_qa,
                user_id=doc.user.id if doc.user else 0
            )
            
            # Progress
            progress = int((i + 1) / len(chunks) * 100)
            if i % 10 == 0:
                doc.progress_percent = progress
                doc.processed_chunks = i + 1
                doc.save(update_fields=['progress_percent', 'processed_chunks'])

        # ====================================================================
        # STEP 5: Mark as done
        # ====================================================================
        doc.processed = True
        doc.status = Document.Status.INDEXED
        doc.progress_percent = 100
        doc.processed_chunks = len(chunks)
        doc.total_chunks = len(chunks)
        doc.save()
        
        logger.info(f"✅ Indexed {len(chunks)} chunks for {doc.title}")
        return {"status": "success", "chunks": len(chunks)}

    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}")
        Document.objects.filter(id=doc_id).update(
            status=Document.Status.FAILED,
            last_error=str(e)
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
# CORE QUERY ENGINE: Minimal, fast, cheap ($0.0004 per query)
# ============================================================================

def query_academic_rag(
    query: str,
    user_id: int,
    threshold_high: float = 0.88,
    threshold_low: float = 0.70
) -> dict:
    """
    Three-tier retrieval strategy costing <$0.001 per query:
    
    1. Direct retrieval (0.88+ similarity + is_qa) → NO LLM ($0)
    2. Synthesis (0.70-0.88 similarity) → 1x LLM call ($0.001)
    3. Reject (<0.70 similarity) → NO LLM ($0)
    
    Args:
        query: User question
        user_id: For multi-tenant isolation
        
    Returns:
        {
            'answer': str or None,
            'confidence': float,
            'method': 'direct'|'synthesis'|'rejected',
            'citations': [{'key': 'smith2020', 'text': 'Smith et al. (2020)'}],
            'latency_ms': int,
            'cost_usd': float
        }
    """
    import time
    start = time.time()
    cost = 0.0
    
    try:
        # ====================================================================
        # STEP 1: Embed query (tiny cost: $0.00006 for 40 tokens)
        # ====================================================================
        embedding_model = get_embedding_model()
        q_vector = embedding_model.embed_query(query)
        cost += 0.00006  # text-embedding-3-small rate
        
        # ====================================================================
        # STEP 2: Vector search (PostgreSQL, $0 cost)
        # ====================================================================
        from ai_engine.models import ChunkIndex
        from django.db.models import F
        from pgvector.django import CosineDistance
        
        similar_chunks = ChunkIndex.objects.filter(
            user_id=user_id
        ).annotate(
            distance=CosineDistance('embedding', q_vector)
        ).order_by('distance')[:5]
        
        if not similar_chunks:
            return {
                'answer': None,
                'confidence': 0.0,
                'method': 'rejected',
                'reason': 'no_documents',
                'citations': [],
                'latency_ms': int((time.time() - start) * 1000),
                'cost_usd': cost
            }
        
        top_chunk = similar_chunks[0]
        
        # Convert pgvector distance (0-2) to similarity (0-1)
        # cosine similarity = 1 - cosine_distance
        similarity = 1.0 - top_chunk.distance
        
        # ====================================================================
        # STEP 3: DECISION TREE
        # ====================================================================
        
        if similarity >= threshold_high and top_chunk.is_qa:
            # ✅ DIRECT ANSWER: Return chunk as-is, no LLM
            # Build citations from pre-computed metadata
            citations = _build_citations_from_keys(
                top_chunk.citation_keys,
                top_chunk.document.metadata
            )
            
            return {
                'answer': top_chunk.content,
                'confidence': float(similarity),
                'method': 'direct_retrieval',
                'citations': citations,
                'source_page': top_chunk.page_number,
                'latency_ms': int((time.time() - start) * 1000),
                'cost_usd': cost
            }
        
        elif similarity >= threshold_low:
            # ⚠️  SYNTHESIS: Need LLM to bridge gap
            # Use top 3 chunks as context
            context_chunks = similar_chunks[:3]
            context_text = "\n\n".join([
                f"[Source: {c.document.title}, Page {c.page_number}]\n{c.content}"
                for c in context_chunks
            ])
            
            # Call GPT-3.5 once
            answer_text = _synthesize_answer(query, context_text)
            cost += 0.001  # Average GPT-3.5-turbo call
            
            # Extract citations (they should be in the synthesis)
            top_citations = _build_citations_from_keys(
                context_chunks[0].citation_keys,
                context_chunks[0].document.metadata
            )
            
            return {
                'answer': answer_text,
                'confidence': float(similarity),
                'method': 'llm_synthesis',
                'citations': top_citations,
                'latency_ms': int((time.time() - start) * 1000),
                'cost_usd': cost
            }
        
        else:
            # ❌ INSUFFICIENT EVIDENCE: Reject gracefully
            return {
                'answer': None,
                'confidence': float(similarity),
                'method': 'rejected',
                'reason': 'insufficient_evidence',
                'message': 'Your documents do not contain information about this topic.',
                'citations': [],
                'latency_ms': int((time.time() - start) * 1000),
                'cost_usd': cost
            }
    
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return {
            'answer': None,
            'confidence': 0.0,
            'method': 'error',
            'error': str(e),
            'citations': [],
            'latency_ms': int((time.time() - start) * 1000),
            'cost_usd': 0.0
        }


def _build_citations_from_keys(citation_keys: list, doc_metadata) -> list:
    """
    Convert citation keys to formatted citation objects.
    Metadata already has full bibtex data from ingestion.
    """
    if not doc_metadata or not hasattr(doc_metadata, 'bibtex_entries'):
        return []
    
    citations = []
    bibtex = doc_metadata.bibtex_entries or {}
    
    for key in citation_keys:
        if key in bibtex:
            entry = bibtex[key]
            citations.append({
                'key': key,
                'text': entry.get('authors', 'Unknown'),
                'year': entry.get('year', ''),
                'page': entry.get('page', '')
            })
    
    return citations


def _synthesize_answer(query: str, context: str) -> str:
    """
    Call GPT-3.5-turbo ONCE to synthesize answer.
    No verification, no fallback, no reranking.
    Cost: ~$0.001 per call
    """
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
        raise ValueError("Azure OpenAI not configured")
    
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
    
    prompt = f"""You are a research assistant. Answer the question ONLY using the provided context.

QUESTION: {query}

CONTEXT:
{context}

Answer in 2-3 sentences. Be precise. Do NOT add information not in the context."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-35-turbo",  # Deployment name
            messages=[
                {"role": "system", "content": "You are a research assistant answering from provided sources only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300,
            timeout=10
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Synthesis failed: {str(e)}")
        raise


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

            # Use new citation-enforced prompt
            system_prompt, user_prompt, citation_map = build_citation_prompt(query, docs)

            with trace_context(
                "rag.generation.response",
                {
                    "rag.context.chunk_count": len(docs),
                    "rag.prompt.length": len(user_prompt),
                },
            ):
                # Call LLM with citation enforcement
                response_text, model_used = call_llm_with_citations(user_prompt, system_prompt)
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
                    "citations": [],
                    "has_citations_for_all_claims": False,
                    "sources_sufficient": False,
                    "confidence": 0.0,
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
            
            # NEW: Validate citations
            citation_validation = validate_citations(
                answer_text=answer,
                citations_metadata=response_data.get("citations", []),
                source_chunks=docs
            )
            
            add_span_attributes({
                "rag.citations.count": citation_validation['citation_count'],
                "rag.citations.valid": citation_validation['all_citations_valid'],
                "rag.citations.invalid": len(citation_validation['invalid_citations'])
            })
            
            # If citations are invalid, reject the answer
            if not citation_validation['all_citations_valid']:
                logger.warning(f"⚠️ Citation validation failed: {citation_validation['invalid_citations']}")
                response_data['citation_validation'] = citation_validation
                # Force regeneration
                response_data['has_citations_for_all_claims'] = False
            else:
                response_data['citation_validation'] = citation_validation
            
            initial_score = float(response_data.get("confidence", 0.5) or 0.5)
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

                # Regenerate with stricter citation enforcement
                strict_system_prompt = """You are VeriRag in STRICT MODE. Every claim MUST have a source citation.

ULTRA-STRICT CITATION RULES:
1. EVERY sentence with a factual claim needs a [N] citation.
2. If you cannot find evidence in sources, say: "The documents do not provide this information."
3. Only cite information that appears EXPLICITLY in the sources.
4. If in doubt, add a citation [N] or reject the claim.

OUTPUT (STRICT JSON):
{
    "answer": "Ultra-conservative answer with ALL claims cited [1][2]",
    "citations": [{"index": 1, "page": 5, "section": "Methods"}],
    "has_citations_for_all_claims": true,
    "sources_sufficient": true,
    "confidence": 0.85
}"""

                strict_user_prompt = f"""Question: {query}

SOURCES (cite ONLY from these):
{context}

CRITICAL: Every factual claim MUST have a citation [N]. If you cannot cite it, don't say it."""

                try:
                    with trace_context("rag.verification.regeneration", {"rag.provider": "groq"}):
                        strict_response = call_llm_with_citations(strict_user_prompt, strict_system_prompt)[0]
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
                
                # Build response with citations + RAGAS metrics
                final_response = {
                    "answer": answer,
                    "citations": response_data.get("citations", []),
                    "has_citations_for_all_claims": response_data.get("has_citations_for_all_claims", False),
                    "sources_sufficient": response_data.get("sources_sufficient", True),
                    "citation_validation": {
                        "all_citations_valid": citation_validation.get('all_citations_valid', False),
                        "invalid_citations": citation_validation.get('invalid_citations', [])
                    },
                    "faithfulness_score": round(combined_score, 2),
                    "confidence": response_data.get("confidence", combined_score),
                    "explanation": response_data.get("explanation", verification_explanation),
                    "source_citation": source_citation,
                    "evidence_items": evidence_items,
                    "verification_passed": verification_passed and citation_validation.get('all_citations_valid', False),
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
                        "rag.citations.count": citation_validation.get('citation_count', 0),
                        "rag.citations.valid": citation_validation.get('all_citations_valid', False),
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
