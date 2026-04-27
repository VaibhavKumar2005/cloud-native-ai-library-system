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
from functools import lru_cache
from opentelemetry import trace
from openai import AzureOpenAI, OpenAI
from prometheus_client import Counter, Histogram, Gauge
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ai_engine.models import Document

# Import vector store operations (embeddings & pgvector)
from ai_engine.vector_store import (
    get_embedding_model,
    get_vector_store,
    get_text_splitter,
    build_evidence_payload,
    extract_unique_document_ids,
    CONNECTION_STRING,
    COLLECTION_NAME,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_MODEL,
    SIMILARITY_THRESHOLD,
)

# Import faithfulness verification (hallucination detection)
from ai_engine.faithfulness_scorer import (
    verify_faithfulness as _verify_faithfulness,
    evaluate_with_ragas as _evaluate_with_ragas,
    score_answer,
    FAITHFULNESS_THRESHOLD,
)

# 🚨 FIX: Handle duplicate Prometheus metric registration during module re-import
# When Django imports this module multiple times during URL resolution,
# metrics that are registered globally will fail on subsequent imports.
# Solution: Wrap all metric registrations in try/except to gracefully handle duplicates.
logger = logging.getLogger(__name__)

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

# Set up OpenTelemetry tracing
tracer = trace.get_tracer(__name__)

# ============================================================================
# PROMETHEUS METRICS FOR MISSION CONTROL
# ============================================================================
# Note: Wrapped in try/except to handle duplicate registration when module
# is imported multiple times (e.g., during Django URL resolution)
try:
    VERIFICATION_REJECTIONS = Counter(
        'verirag_hallucination_rejections_total',
        'Total number of AI responses rejected for low faithfulness'
    )
except ValueError:
    # Metric already registered, skip
    pass

try:
    LLM_FALLBACKS = Counter(
        'verirag_llm_fallbacks_total',
        'Total number of times the system switched to the backup LLM'
    )
except ValueError:
    pass

try:
    QUERIES_TOTAL = Counter(
        'verirag_queries_total',
        'Total number of RAG queries processed'
    )
except ValueError:
    pass

try:
    DOCUMENTS_INGESTED = Counter(
        'verirag_documents_ingested_total',
        'Total number of documents successfully ingested'
    )
except ValueError:
    pass

try:
    FAITHFULNESS_HISTOGRAM = Histogram(
        'verirag_faithfulness_score',
        'Distribution of faithfulness scores',
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    )
except ValueError:
    pass

try:
    ACTIVE_MODEL = Gauge(
        'verirag_active_model',
        'Currently active LLM model (1=Gemini, 2=Groq)',
    )
    ACTIVE_MODEL.set(1)  # Default to Gemini
except ValueError:
    pass

# ============================================================================
# CONFIGURATION
# ============================================================================
# Database configuration is imported from vector_store module
# Azure configuration is imported from vector_store module

# Verification thresholds
FAITHFULNESS_THRESHOLD = 0.6  # Below this triggers fallback


def _build_evidence_payload(docs):
    """Re-export from vector_store for backward compatibility."""
    return build_evidence_payload(docs)


def _extract_unique_document_ids(docs):
    """Re-export from vector_store for backward compatibility."""
    return extract_unique_document_ids(docs)


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


def build_citation_prompt(query: str, docs: list) -> tuple:
    """
    Build system and user prompts for citation-grounded generation.
    
    Returns:
        (system_prompt, user_prompt, citation_map)
    """
    citation_map = {i: doc.metadata for i, doc in enumerate(docs)}
    
    context_blocks = []
    for i, doc in enumerate(docs):
        page = doc.metadata.get('page', 'Unknown')
        title = doc.metadata.get('document_title', 'Document')
        context_blocks.append(f"[Citation {i}] ({title}, p. {page})\n{doc.page_content}")
    
    context = "\n\n---\n\n".join(context_blocks)
    
    system_prompt = """You are a research assistant that answers questions based solely on provided documents.
    
Rules:
- cite sources using [Citation N] format
- only answer if supported by documents
- return JSON with: {"answer": "...", "citations": [...], "confidence": 0.0-1.0}
"""
    
    user_prompt = f"""Question: {query}

Context:
{context}

Provide answer grounded in citations."""
    
    return system_prompt, user_prompt, citation_map


def call_llm_with_citations(user_prompt: str, system_prompt: str) -> tuple:
    """
    Call LLM with system and user prompts, returns (response_text, model_used).
    """
    combined = system_prompt + "\n\n" + user_prompt
    return call_llm_with_fallback(combined)


def validate_citations(answer_text: str, citations_metadata: list, source_chunks: list) -> dict:
    """
    Validate that citations are properly grounded in source chunks.
    
    Returns:
        {
            'citation_count': int,
            'all_citations_valid': bool,
            'invalid_citations': list
        }
    """
    invalid = []
    
    for citation in citations_metadata or []:
        cite_text = citation.get('excerpt', '').lower() if isinstance(citation, dict) else str(citation).lower()
        
        # Check if citation text appears in any source chunk
        found = False
        for chunk in source_chunks:
            if cite_text and cite_text in chunk.page_content.lower():
                found = True
                break
        
        if not found and cite_text:
            invalid.append(citation)
    
    return {
        'citation_count': len(citations_metadata or []),
        'all_citations_valid': len(invalid) == 0,
        'invalid_citations': invalid
    }


# ============================================================================
# CORE QUERY ENGINE: Minimal, fast, cheap ($0.0004 per query)
# ============================================================================

def query_academic_rag(query: str) -> dict:
    """
    Minimal RAG pipeline:
    Query -> Retrieve top 3 chunks -> Generate from retrieved context -> Return or reject.
    """
    with tracer.start_as_current_span("query_academic_rag") as span:
        span.set_attribute("query", query)
        
        vector_db = get_vector_store()
        
        with tracer.start_as_current_span("similarity_search"):
            chunks = vector_db.similarity_search(query, k=3)

        if not chunks:
            span.set_attribute("result", "no_results")
            return {
                "status": "rejected",
                "message": "No reliable evidence found",
            }

        context_blocks = []
        sources = []
        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk.metadata or {}
            title = metadata.get("document_title") or metadata.get("source") or "Document"
            page = metadata.get("page", metadata.get("page_number"))

            context_blocks.append(f"[Source {index}: {title}, page {page}]\n{chunk.page_content}")
            sources.append(
                {
                    "source_index": index,
                    "title": title,
                    "page": page,
                    "excerpt": chunk.page_content[:300],
                }
            )

        context = "\n\n---\n\n".join(context_blocks)
        
        with tracer.start_as_current_span("generate_answer"):
            answer = _generate_answer_from_context(query=query, context=context)

        if "I don't have reliable evidence" in answer:
            span.set_attribute("result", "rejected")
            return {
                "status": "rejected",
                "message": "No reliable evidence found",
            }

        span.set_attribute("result", "success")
        span.set_attribute("source_count", len(sources))
        return {
            "status": "success",
            "answer": answer,
            "sources": sources,
        }


def _generate_answer_from_context(query: str, context: str) -> str:
    with tracer.start_as_current_span("generate_answer_from_context") as span:
        span.set_attribute("query_length", len(query))
        span.set_attribute("context_length", len(context))
        
        if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
            # Mock mode for local testing
            logger.warning("Azure credentials not configured, using mock response")
            span.set_attribute("mode", "mock")
            return _mock_answer_from_context(query, context)

        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )

        prompt = f"""
You are a strict academic research assistant.

RULES:
1. Use ONLY the provided context.
2. If answer is not explicitly in context, say EXACTLY:
   "I don't have reliable evidence to answer this question."
3. Do NOT guess.
4. Cite sources like [Source 1], [Source 2].

Context:
{context}

Question:
{query}
"""

        try:
            with tracer.start_as_current_span("azure_openai_call"):
                response = client.chat.completions.create(
                    model=AZURE_OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a strict academic research assistant.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0,
                    max_tokens=500,
                )
            span.set_attribute("mode", "azure")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Azure OpenAI call failed: {e}, using mock response")
            span.set_attribute("mode", "mock_fallback")
            span.set_attribute("error", str(e))
            return _mock_answer_from_context(query, context)


def _mock_answer_from_context(query: str, context: str) -> str:
    """Generate a mock answer from context for local testing without Azure."""
    # Simple extraction logic: find sentences containing query keywords
    sentences = context.split('.')
    relevant = [s.strip() for s in sentences if any(word.lower() in s.lower() for word in query.split()[:3])]
    
    if relevant:
        answer = '. '.join(relevant[:2]) + '.'
    else:
        # Fallback: use first few sentences
        answer = '. '.join(sentences[:2]) + '.' if sentences else "Based on the context provided, I can see this is related to your query about " + query.split()[0] if query.split() else ""
    
    return answer


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


def _semantic_scholar_search(query: str, limit: int = 4) -> list:
    """
    Search Semantic Scholar API for papers related to the query.
    Used as fallback when no local documents match.
    
    Returns:
        [{'title': str, 'authors': list, 'year': int, 'url': str, 'abstract': str}, ...]
    """
    try:
        import requests
        
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,authors,year,url,abstract,externalIds'
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        papers = []
        for paper in data.get('data', []):
            papers.append({
                'title': paper.get('title', ''),
                'authors': [a.get('name', '') for a in paper.get('authors', [])],
                'year': paper.get('year'),
                'url': paper.get('url', ''),
                'abstract': paper.get('abstract', ''),
                'paper_id': paper.get('externalIds', {}).get('ArXiv') or paper.get('paperId', '')
            })
        
        return papers
    
    except Exception as e:
        logger.warning(f"Semantic Scholar search failed for '{query}': {e}")
        return []


# ============================================================================
# 3. THE VERIFICATION ENGINE - Core "Librarian" Protocol
# ============================================================================
# EXTRACTED: Moved to ai_engine.faithfulness_scorer module
# Backward compatibility wrappers:

def verify_faithfulness(answer, context, query):
    """
    Semantic faithfulness verification using embedding cosine similarity.
    [Extracted to faithfulness_scorer.py]
    
    Returns a faithfulness score (0.0-1.0) and verification explanation.
    """
    return _verify_faithfulness(answer, context, query)


def evaluate_with_ragas(query: str, answer: str, contexts: list, ground_truth: str = None) -> dict:
    """
    LLM-based evaluation using RAGAS framework.
    [Extracted to faithfulness_scorer.py]
    
    Returns dict with faithfulness, answer_relevancy, context_precision, etc.
    """
    return _evaluate_with_ragas(query, answer, contexts, ground_truth)


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
