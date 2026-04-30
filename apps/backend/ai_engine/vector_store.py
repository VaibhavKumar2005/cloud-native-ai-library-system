"""
Vector Store Module - PostgreSQL pgvector & Embeddings Management
Handles vector database operations, embedding generation, and retrieval.
"""

import os
import logging
import hashlib
from functools import lru_cache
from langchain_community.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


# ============================================================================
# MOCK EMBEDDINGS FOR LOCAL TESTING (NO AZURE REQUIRED)
# ============================================================================
class MockEmbeddings:
    """Simple deterministic embeddings for local testing without Azure."""
    
    def __init__(self, dimension=1536):
        self.dimension = dimension
    
    def embed_documents(self, texts):
        """Generate deterministic embeddings for a list of documents."""
        return [self._hash_to_embedding(text) for text in texts]
    
    def embed_query(self, text):
        """Generate deterministic embedding for a query."""
        return self._hash_to_embedding(text)
    
    def _hash_to_embedding(self, text):
        """Convert text to deterministic embedding using hash."""
        # Create a hash that's deterministic
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Seed random with hash for reproducibility
        import random
        random.seed(hash_val)
        # Generate embedding with seed
        embedding = [random.gauss(0, 0.1) for _ in range(self.dimension)]
        # Normalize
        norm = sum(x**2 for x in embedding) ** 0.5
        return [x / (norm + 1e-8) for x in embedding]


def sanitize_utf8_text(value):
    """Normalize text before sending it to PGVector/psycopg."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", "replace").decode("utf-8")

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "devpassword")
DB_HOST = os.environ.get("POSTGRES_HOST", "rag-db")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "verirag_db")

CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
COLLECTION_NAME = os.environ.get("PGVECTOR_COLLECTION_NAME", "verirag_documents")

# ============================================================================
# AZURE OPENAI EMBEDDINGS CONFIGURATION
# ============================================================================
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
# Try both variable names for backward compatibility
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4-turbo"
USE_MOCK_EMBEDDINGS = os.environ.get("USE_MOCK_EMBEDDINGS", "false").strip().lower() == "true"

# Vector search thresholds
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score for context


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Creates Azure OpenAI embedding model (text-embedding-3-large for academic accuracy).
    Falls back to MockEmbeddings for local testing without Azure.
    Uses Azure Key Vault or environment variables for credentials.
    Cached at module level to avoid recreating connection on every request.
    
    Returns:
        AzureOpenAIEmbeddings or MockEmbeddings: Initialized embeddings model
    """
    # Explicit local override for demo/testing stability
    if USE_MOCK_EMBEDDINGS:
        logger.info("Using mock embeddings (USE_MOCK_EMBEDDINGS=true)")
        return MockEmbeddings()

    # Try Azure first
    if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY:
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            return AzureOpenAIEmbeddings(
                model="text-embedding-3-large",  # 3072 dimensions for better accuracy
                api_version="2024-02-15-preview",
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_KEY
            )
        except Exception as e:
            logger.warning(f"Azure OpenAI embeddings failed: {e}, falling back to mock embeddings")
    
    # Fallback to mock embeddings for local testing
    logger.info("Using mock embeddings (local testing mode)")
    return MockEmbeddings()


@lru_cache(maxsize=1)
def get_vector_store():
    """
    Gets the configured PGVector store with PostgreSQL pgvector extension.
    Cached at module level to reuse connection.
    
    Returns:
        PGVector: Initialized vector store connected to PostgreSQL
    """
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embedding_function=get_embedding_model(),
    )


def replace_document_chunks(document_id, texts, metadatas, previous_count=0):
    """
    Replace a document's indexed chunks in PGVector using stable IDs.

    This keeps ingestion aligned with the retrieval path used by query_academic_rag.
    """
    if len(texts) != len(metadatas):
        raise ValueError("texts and metadatas must have the same length")

    vector_store = get_vector_store()
    ids = [f"doc:{document_id}:chunk:{index}" for index in range(len(texts))]
    stale_ids = [
        f"doc:{document_id}:chunk:{index}"
        for index in range(max(len(texts), previous_count))
    ]

    if stale_ids:
        try:
            vector_store.delete(ids=stale_ids, collection_only=True)
        except Exception as exc:
            logger.warning("Unable to delete existing vectors for document %s: %s", document_id, exc)

    if ids:
        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    return ids


def get_text_splitter(chunk_size=1000, chunk_overlap=200):
    """
    Creates a text splitter for document chunking.
    
    Args:
        chunk_size (int): Size of each chunk in tokens
        chunk_overlap (int): Overlap between consecutive chunks
        
    Returns:
        RecursiveCharacterTextSplitter: Configured splitter
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )


def build_evidence_payload(docs):
    """
    Builds evidence payload from retrieved documents.
    Formats document chunks with metadata for display.
    
    Args:
        docs (list): List of retrieved document chunks
        
    Returns:
        list: Formatted evidence items with source metadata
    """
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


def extract_unique_document_ids(docs):
    """
    Extracts unique document IDs from retrieved chunks.
    
    Args:
        docs (list): List of document chunks
        
    Returns:
        list: Sorted list of unique document IDs
    """
    document_ids = []
    for doc in docs:
        document_id = doc.metadata.get("document_id")
        if document_id is not None:
            document_ids.append(str(document_id))
    return sorted(set(document_ids))
