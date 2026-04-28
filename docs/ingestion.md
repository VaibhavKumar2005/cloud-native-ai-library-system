# PDF & Paper Ingestion Pipeline

This document describes how VeriRAG processes academic papers into queryable vectors.

---

## Overview

```
PDF Upload
    ↓
[1] TEXT EXTRACTION    → PyPDF2, OCR
    ↓
[2] PREPROCESSING      → Clean, normalize
    ↓
[3] CHUNKING           → Fixed-size with overlap
    ↓
[4] EMBEDDING          → Google text-embedding-004
    ↓
[5] STORAGE            → PostgreSQL + pgvector
    ↓
[6] INDEXING           → Create HNSW index
    ↓
Ready for Retrieval
```

---

## Stage 1: Text Extraction

### PDF Processing

```python
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF with metadata.
    """
    reader = PdfReader(pdf_path)
    
    documents = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        
        doc = {
            'page_number': page_num + 1,
            'content': text,
            'source': pdf_path.name
        }
        documents.append(doc)
    
    return documents
```

**Limitations**:
- OCR not automatically triggered (scanned PDFs return empty text)
- Tables may extract as garbled text
- Headers/footers may be included

### Handling Scanned PDFs (Optional)

For scanned papers, enable OCR:

```python
from pdf2image import convert_from_path
import pytesseract

def extract_text_with_ocr(pdf_path):
    """
    Extract text from scanned PDF using Tesseract OCR.
    """
    images = convert_from_path(pdf_path)
    
    full_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        full_text += text + "\n"
    
    return full_text
```

**Cost**: OCR is computationally expensive (not enabled by default)  
**Recommendation**: Enable only for scanned papers that fail text extraction

---

## Stage 2: Preprocessing

### Text Normalization

```python
def preprocess_text(text):
    """
    Clean and normalize extracted text.
    """
    import re
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common artifacts
    text = re.sub(r'\x00', '', text)  # Null bytes
    text = re.sub(r'[\r\n]{3,}', '\n\n', text)  # Excessive line breaks
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    
    return text.strip()
```

### Metadata Extraction

```python
def extract_metadata(pdf_path):
    """
    Extract paper metadata from PDF.
    """
    reader = PdfReader(pdf_path)
    
    metadata = {
        'title': reader.metadata.get('/Title', 'Unknown'),
        'authors': reader.metadata.get('/Author', 'Unknown'),
        'creation_date': reader.metadata.get('/CreationDate'),
        'subject': reader.metadata.get('/Subject'),
        'pages': len(reader.pages),
    }
    
    return metadata
```

---

## Stage 3: Chunking Strategy

### Fixed-Size Chunking (Current)

```python
def chunk_text_fixed(text, chunk_size=512, overlap=0.5):
    """
    Divide text into fixed-size chunks with overlap.
    
    Args:
        text: Full document text
        chunk_size: Tokens per chunk (~4 chars = 1 token, so 512 tokens ≈ 2048 chars)
        overlap: 0.5 = 50% overlap between consecutive chunks
    """
    words = text.split()
    
    # Convert word count to approximate tokens
    # Rough heuristic: 1 word ≈ 1.3 tokens
    chunk_word_size = int(chunk_size / 1.3)
    overlap_size = int(chunk_word_size * overlap)
    stride = chunk_word_size - overlap_size
    
    chunks = []
    
    for i in range(0, len(words), stride):
        chunk_words = words[i:i + chunk_word_size]
        chunk_text = " ".join(chunk_words)
        
        chunks.append({
            'content': chunk_text,
            'start_word': i,
            'word_count': len(chunk_words)
        })
    
    return chunks
```

**Advantages**:
- Simple, predictable
- Deterministic (same input = same chunks)
- Efficient

**Disadvantages**:
- May split sentences mid-phrase
- No semantic awareness
- Context can be lost at boundaries

**Configuration**:
- Chunk size: 512 tokens (balance between precision and coverage)
- Overlap: 50% (ensures context preservation)
- Typical chunks: 200-250 words

### Advanced: Semantic Chunking (Future)

```python
def chunk_text_semantic(text, model="all-MiniLM-L6-v2"):
    """
    Divide text by semantic boundaries (sentences/paragraphs).
    Not currently implemented, but planned improvement.
    
    Benefits:
    - Respects document structure
    - Better context preservation
    - Improved retrieval accuracy
    """
    # Split by paragraph first
    paragraphs = text.split('\n\n')
    
    chunks = []
    for para in paragraphs:
        if len(para) > 512:
            # Split paragraph if too large
            # Would use semantic segmentation here
            pass
        else:
            chunks.append(para)
    
    return chunks
```

---

## Stage 4: Embedding

### Vector Generation

```python
from langchain.embeddings import GooglePalmEmbeddings

def embed_chunks(chunks, model_name="models/text-embedding-004"):
    """
    Convert text chunks to vectors.
    """
    embedding_model = GooglePalmEmbeddings(
        model_name=model_name,
        google_api_key=GOOGLE_API_KEY
    )
    
    embeddings = []
    
    for chunk in chunks:
        # Embed the chunk content
        vector = embedding_model.embed_query(chunk['content'])
        
        embeddings.append({
            'content': chunk['content'],
            'vector': vector,  # 512-dimensional
            'vector_dimension': len(vector)
        })
    
    return embeddings
```

### Cost Calculation

```
Vector Dimension: 512
Cost per 1K tokens: $0.00006

For a typical 10-page paper:
  - Words: ~5,000
  - Tokens: ~6,500 (1.3x words)
  - Cost: $0.00006 × (6,500/1,000) = $0.00039
  
Monthly (100 papers):
  - Embedding cost: $0.039
```

---

## Stage 5: Storage in PostgreSQL

### Schema

```sql
-- Papers table
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    publication_date DATE,
    source_url TEXT,
    upload_date TIMESTAMP DEFAULT NOW(),
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Document chunks with embeddings
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL,
    page_number INTEGER,
    chunk_order INTEGER,
    content TEXT NOT NULL,
    embedding vector(512),  -- pgvector extension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

-- Create index for similarity search
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### Insertion

```python
import psycopg2
from psycopg2.extras import execute_values

def store_embeddings(connection, paper_id, chunks):
    """
    Store chunks and embeddings in PostgreSQL.
    """
    cursor = connection.cursor()
    
    data = []
    for chunk_order, chunk in enumerate(chunks):
        data.append((
            paper_id,
            chunk.get('page_number'),
            chunk_order,
            chunk['content'],
            chunk['vector'],  # 512-dim vector
            {
                'word_count': chunk.get('word_count'),
                'source': chunk.get('source')
            }
        ))
    
    # Batch insert for efficiency
    query = """
        INSERT INTO document_chunks 
        (paper_id, page_number, chunk_order, content, embedding, metadata)
        VALUES %s
    """
    execute_values(cursor, query, data)
    
    connection.commit()
```

---

## Stage 6: Indexing

### HNSW Index Creation

```sql
-- Create Hierarchical Navigable Small Worlds index
-- Optimized for similarity search
CREATE INDEX idx_chunk_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m=16, ef_construction=64);
```

**Parameters**:
- `m=16`: Max connections per layer (balance: search speed vs. memory)
- `ef_construction=64`: Construction parameter (higher = better quality, slower build)
- `vector_cosine_ops`: Distance metric (L2, cosine, or inner product)

**Performance Impact**:
- Index size: ~5 bytes per dimension per vector = 2.56 KB per vector
- For 1M vectors: ~2.5 GB index size
- Search latency: 50-100ms typical

---

## Complete Ingestion Pipeline (End-to-End)

```python
import asyncio
from pathlib import Path

async def ingest_paper(pdf_path, user_id, connection):
    """
    Complete pipeline: Extract → Chunk → Embed → Store
    """
    
    print(f"Ingesting: {pdf_path}")
    
    # [1] Extract text
    print("  [1] Extracting text...")
    pages = extract_text_from_pdf(pdf_path)
    metadata = extract_metadata(pdf_path)
    
    # [2] Preprocess
    print("  [2] Preprocessing...")
    processed_pages = [preprocess_text(p['content']) for p in pages]
    
    # [3] Create chunks
    print("  [3] Chunking...")
    all_chunks = []
    for page_num, text in enumerate(processed_pages):
        chunks = chunk_text_fixed(text, chunk_size=512, overlap=0.5)
        for chunk in chunks:
            chunk['page_number'] = page_num + 1
        all_chunks.extend(chunks)
    
    print(f"      Created {len(all_chunks)} chunks")
    
    # [4] Embed
    print("  [4] Embedding (may take a minute)...")
    embeddings = embed_chunks(all_chunks)
    
    # [5] Store
    print("  [5] Storing in database...")
    
    # Insert paper metadata
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO papers (title, authors, upload_date, user_id)
        VALUES (%s, %s, NOW(), %s)
        RETURNING id
    """, (metadata['title'], metadata['authors'], user_id))
    
    paper_id = cursor.fetchone()[0]
    
    # Insert chunks with embeddings
    store_embeddings(connection, paper_id, embeddings)
    
    print(f"  ✅ Complete! Paper ID: {paper_id}")
    
    return paper_id

# Usage
# python -c "
# import asyncio
# asyncio.run(ingest_paper('paper.pdf', user_id=1, connection=db_conn))
# "
```

---

## Monitoring Ingestion

### Progress Tracking

```python
def monitor_ingestion(paper_id):
    """
    Track ingestion progress for user.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*) as total_chunks,
               COUNT(DISTINCT page_number) as pages_indexed,
               MIN(created_at) as started,
               MAX(created_at) as last_update
        FROM document_chunks
        WHERE paper_id = %s
    """, (paper_id,))
    
    result = cursor.fetchone()
    
    return {
        'chunks_indexed': result[0],
        'pages_indexed': result[1],
        'started': result[2],
        'last_update': result[3],
        'status': 'INDEXING' if result[1] > 0 else 'QUEUED'
    }
```

### Error Handling

```python
def handle_ingestion_error(pdf_path, error):
    """
    Graceful error handling during ingestion.
    """
    errors = {
        'OCR_REQUIRED': 'PDF is scanned. Enable OCR in settings.',
        'CORRUPTED_PDF': 'PDF appears corrupted. Try re-saving.',
        'EMBEDDING_FAILED': 'Google API unavailable. Retry later.',
        'DB_ERROR': 'Database connection failed. Check server.'
    }
    
    logger.error(f"Ingestion failed: {error}")
    return errors.get(error.type, 'Unknown error')
```

---

## Performance Optimization

### Batch Processing

For multiple papers:

```python
async def batch_ingest_papers(pdf_directory, user_id, connection):
    """
    Ingest multiple papers efficiently.
    """
    pdfs = Path(pdf_directory).glob("*.pdf")
    
    # Queue papers
    queue = asyncio.Queue()
    for pdf in pdfs:
        await queue.put(pdf)
    
    # Process with limited concurrency (avoid API rate limits)
    workers = []
    for _ in range(3):  # 3 concurrent embeddings
        worker = asyncio.create_task(
            ingest_worker(queue, user_id, connection)
        )
        workers.append(worker)
    
    await queue.join()
    
    print(f"✅ Ingested {len(list(pdfs))} papers")
```

### Cost Optimization

```
Strategy: Batch embedding requests

Instead of:
  - 100 chunks → 100 API calls ($0.006)

Use:
  - 100 chunks → 1 batch call ($0.0006)
  - Savings: 90% reduction

Implementation:
  - Group chunks by paper
  - Send 50 chunks per API request
  - Implement exponential backoff for failures
```

---

## Data Quality Checks

### Pre-Storage Validation

```python
def validate_chunk(chunk):
    """
    Verify chunk quality before storing.
    """
    checks = {
        'has_content': len(chunk['content']) > 10,
        'not_duplicate': chunk['content'] != previous_chunk,
        'embedding_valid': len(chunk['vector']) == 512,
        'embedding_normalized': -1 <= chunk['vector'][0] <= 1,
        'no_excessive_newlines': chunk['content'].count('\n') < 5,
    }
    
    if not all(checks.values()):
        logger.warning(f"Chunk validation failed: {checks}")
        return False
    
    return True
```

---

## Supported Paper Sources

### Currently Supported
1. **PDF files** (uploaded via UI)
2. **Plain text** (.txt files)

### Planned Support
- **arXiv papers** (direct API integration)
- **Semantic Scholar** (metadata + abstract)
- **Google Scholar** (via web scraping)
- **bioRxiv / medRxiv** (preprint servers)

---

See also: [RAG Pipeline](rag_pipeline.md), [Evaluation](evaluation.md)
