"""
VeriRag AI Engine - Complete Verification Logic
Implements the "Librarian" verification protocol with hallucination detection
and automatic failover to Groq/Llama-3.
"""

import os
import json
import logging
import re
import hvac  # For HashiCorp Vault
import google.generativeai as genai
from openai import OpenAI  # Used for the Groq Fallback
from prometheus_client import Counter, Histogram, Gauge
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import PGVector
from ai_engine.models import Document

# Import tracing utilities (graceful fallback if not configured)
try:
    from ai_engine.tracing import trace_span, trace_context, add_span_attributes, record_event
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
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "library_db")

CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
COLLECTION_NAME = "rag_collection"

# Verification thresholds
FAITHFULNESS_THRESHOLD = 0.6  # Below this triggers fallback
SIMILARITY_THRESHOLD = 0.7    # Minimum similarity score for context

# ============================================================================
# VAULT INTEGRATION - SECURE API KEY RETRIEVAL
# ============================================================================
_api_key_cache = {"key": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutes

def get_api_key_from_vault(key_name="GOOGLE_API_KEY"):
    """
    Retrieves API keys dynamically from HashiCorp Vault with caching.
    Falls back to environment variables if Vault is unavailable.
    """
    import time
    
    cache_key = f"{key_name}_cached"
    current_time = time.time()
    
    # Check cache first
    if _api_key_cache.get(cache_key) and (current_time - _api_key_cache.get("timestamp", 0)) < CACHE_TTL:
        return _api_key_cache[cache_key]
    
    try:
        vault_url = os.environ.get('VAULT_ADDR', 'http://vault:8200')
        vault_token = os.environ.get('VAULT_TOKEN')
        
        if not vault_token:
            logger.warning("VAULT_TOKEN not set, falling back to environment variables")
            return os.environ.get(key_name)
        
        client = hvac.Client(url=vault_url, token=vault_token)
        
        if not client.is_authenticated():
            logger.error("Vault authentication failed")
            return os.environ.get(key_name)
        
        # Try to read from KV v2 secrets engine
        secret_response = client.secrets.kv.v2.read_secret_version(
            path='myapp',
            mount_point='secret'
        )
        
        api_key = secret_response['data']['data'].get(key_name)
        
        if api_key:
            # Cache the successful retrieval
            _api_key_cache[cache_key] = api_key
            _api_key_cache["timestamp"] = current_time
            logger.info(f"✅ Successfully retrieved {key_name} from Vault")
            return api_key
        
        logger.warning(f"{key_name} not found in Vault, falling back to environment")
        return os.environ.get(key_name)
        
    except Exception as e:
        logger.error(f"Vault Security Error: {str(e)} - Falling back to environment variable")
        return os.environ.get(key_name)


def get_groq_api_key():
    """Retrieves Groq API key from Vault or environment."""
    return get_api_key_from_vault("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")


def get_embedding_model():
    """Creates embedding model with Vault-sourced API key."""
    api_key = get_api_key_from_vault("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from Vault and environment!")
    
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )


# ============================================================================
# 1. THE INGESTION ENGINE - PDF Processing Pipeline
# ============================================================================
def ingest_document(doc_id):
    """
    Takes a Document ID and processes the PDF into vector embeddings.
    Uses LangChain's RecursiveCharacterTextSplitter for optimal chunking.
    """
    try:
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        logger.info(f"📄 Starting ingestion for: {doc.title}")

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

        # Step 3: Enrich metadata for multi-tenant isolation
        for i, chunk in enumerate(chunks):
            chunk.metadata["user_id"] = str(doc.user.id) if doc.user else "public"
            chunk.metadata["document_id"] = str(doc.id)
            chunk.metadata["document_title"] = doc.title
            chunk.metadata["chunk_index"] = i

        # Step 4: Generate embeddings and store in PGVector
        PGVector.from_documents(
            embedding=get_embedding_model(),
            documents=chunks,
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            pre_delete_collection=False
        )

        # Step 5: Update document status
        doc.processed = True
        doc.save()
        
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
def call_gemini(prompt, api_key):
    """Primary LLM: Google Gemini with JSON mode."""
    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.1,  # Low temperature for factual responses
        "response_mime_type": "application/json"
    }
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
    response = model.generate_content(prompt)
    return response.text


def call_groq_llama(prompt):
    """Backup LLM: Groq's Llama-3 for failover."""
    groq_key = get_groq_api_key()
    if not groq_key:
        raise ValueError("GROQ_API_KEY not available in Vault or environment")
    
    client = OpenAI(
        api_key=groq_key,
        base_url="https://api.groq.com/openai/v1"
    )
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
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
    return response.choices[0].message.content


def call_llm_with_fallback(prompt, api_key):
    """
    Intelligent LLM router: Tries Gemini first, automatically fails over to Groq.
    Updates Prometheus metrics on failover.
    """
    try:
        ACTIVE_MODEL.set(1)  # Gemini
        response = call_gemini(prompt, api_key)
        return response, "gemini"
        
    except Exception as primary_error:
        LLM_FALLBACKS.inc()
        ACTIVE_MODEL.set(2)  # Groq
        logger.warning(f"⚠️ Gemini failed: {primary_error}. Switching to Groq/Llama-3...")
        
        try:
            response = call_groq_llama(prompt)
            return response, "groq"
            
        except Exception as backup_error:
            logger.error(f"❌ Both LLMs failed. Gemini: {primary_error}, Groq: {backup_error}")
            return json.dumps({
                "answer": "System Notice: All AI providers are currently unavailable. Please try again later.",
                "faithfulness_score": 0.0,
                "explanation": "Both primary (Gemini) and backup (Groq) LLMs failed.",
                "source_citation": "System Error",
                "verification_passed": False
            }), "error"


# ============================================================================
# 3. THE VERIFICATION ENGINE - Core "Librarian" Protocol
# ============================================================================
def verify_faithfulness(answer, context, query):
    """
    Second-pass verification: Checks if the generated answer is faithful to the context.
    Returns a faithfulness score and verification status.
    """
    # Simple heuristic checks for obvious hallucinations
    answer_lower = answer.lower()
    context_lower = context.lower()
    
    # Check 1: Key terms from answer should appear in context
    answer_words = set(re.findall(r'\b\w{4,}\b', answer_lower))
    context_words = set(re.findall(r'\b\w{4,}\b', context_lower))
    
    if not answer_words:
        return 0.5, "Unable to extract key terms from answer"
    
    overlap = answer_words.intersection(context_words)
    coverage = len(overlap) / len(answer_words) if answer_words else 0
    
    # Check 2: Answer should not introduce completely new concepts
    new_terms = answer_words - context_words
    novelty_penalty = min(len(new_terms) * 0.05, 0.3)
    
    # Calculate base score
    base_score = coverage - novelty_penalty
    
    # Normalize to 0-1 range
    final_score = max(0.0, min(1.0, base_score + 0.3))  # +0.3 baseline
    
    explanation = f"Term overlap: {len(overlap)}/{len(answer_words)}, New terms: {len(new_terms)}"
    
    return final_score, explanation


def get_verified_answer(query, user_id):
    """
    The complete VeriRag verification pipeline:
    1. Similarity search in PGVector
    2. Generate response using Gemini
    3. Verify faithfulness against raw context
    4. If faithfulness < threshold, regenerate with Groq/Llama-3
    5. Return standardized JSON with integrity metrics
    """
    QUERIES_TOTAL.inc()
    
    try:
        api_key = get_api_key_from_vault("GOOGLE_API_KEY")
        if not api_key:
            return {
                "answer": "System Error: Unable to retrieve API credentials from Vault",
                "faithfulness_score": 0.0,
                "explanation": "Vault connection failed or GOOGLE_API_KEY not found",
                "source_citation": "System Error",
                "verification_passed": False,
                "model_used": "none"
            }

        # Step 1: Connect to PGVector and perform similarity search
        vector_db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )
        
        # Retrieve top 5 relevant chunks with user isolation
        docs = vector_db.similarity_search(
            query,
            k=5,
            filter={"user_id": str(user_id)}
        )
        
        if not docs:
            return {
                "answer": "I couldn't find any relevant information in your uploaded documents. Please upload a document first or rephrase your question.",
                "faithfulness_score": 0.0,
                "explanation": "No matching vectors found for this user's document collection.",
                "source_citation": "None",
                "verification_passed": True,
                "model_used": "none"
            }

        # Build rich context with source citations
        context_parts = []
        citations = []
        for i, doc in enumerate(docs):
            page = doc.metadata.get('page', 'Unknown')
            title = doc.metadata.get('document_title', 'Document')
            context_parts.append(f"[Source {i+1}: {title}, Page {page}]\n{doc.page_content}")
            citations.append(f"{title} (Page {page})")
        
        context = "\n\n---\n\n".join(context_parts)
        source_citation = "; ".join(set(citations))

        # Step 2: Generate initial response with Gemini
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

        response_text, model_used = call_llm_with_fallback(generation_prompt, api_key)
        
        # Parse the response
        try:
            # Clean up JSON in case of markdown wrapping
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
                "verification_passed": False,
                "model_used": model_used
            }

        # Step 3: Second-pass verification
        answer = response_data.get("answer", "")
        initial_score = response_data.get("faithfulness_score", 0.0)
        
        # Run our own verification
        verification_score, verification_explanation = verify_faithfulness(answer, context, query)
        
        # Combine scores (weighted average)
        combined_score = (initial_score * 0.6) + (verification_score * 0.4)
        
        # Record in histogram
        FAITHFULNESS_HISTOGRAM.observe(combined_score)
        
        # Step 4: Check if verification passed
        verification_passed = combined_score >= FAITHFULNESS_THRESHOLD
        
        if not verification_passed:
            # Increment hallucination prevention counter
            VERIFICATION_REJECTIONS.inc()
            logger.warning(f"⚠️ Low faithfulness detected ({combined_score:.2f}). Triggering verification protocol...")
            
            # Try to regenerate with stricter prompt via backup model
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
                strict_response = call_groq_llama(strict_prompt)
                strict_data = json.loads(strict_response)
                
                # Use the stricter response
                response_data = strict_data
                model_used = "groq_verification"
                LLM_FALLBACKS.inc()
                
            except Exception as e:
                logger.error(f"Strict regeneration failed: {e}")
                # Keep original response but flag it
                response_data["explanation"] = f"⚠️ Low confidence ({combined_score:.2f}): {response_data.get('explanation', '')}"

        # Step 5: Build final response
        return {
            "answer": response_data.get("answer", "Unable to generate response"),
            "faithfulness_score": round(combined_score, 2),
            "explanation": response_data.get("explanation", verification_explanation),
            "source_citation": response_data.get("source_citation", source_citation),
            "verification_passed": verification_passed,
            "model_used": model_used,
            "context_chunks_used": len(docs)
        }

    except Exception as e:
        logger.error(f"❌ Verification engine error: {str(e)}")
        return {
            "answer": "An internal error occurred while processing your question.",
            "faithfulness_score": 0.0,
            "explanation": str(e),
            "source_citation": "System Error",
            "verification_passed": False,
            "model_used": "none"
        }