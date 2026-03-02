# 📡 VeriRAG API Specification

> Complete REST API reference for the VeriRAG Cloud-Native AI Library System.  
> **Base URL:** `http://localhost:8000`

---

## Authentication

VeriRAG uses **JWT (JSON Web Tokens)** via `djangorestframework-simplejwt`. All endpoints except `/api/token/` and `/api/health/` require a valid `Authorization: Bearer <token>` header.

### Obtain Token Pair

| | |
|---|---|
| **Endpoint** | `POST /api/token/` |
| **Auth** | None |
| **Description** | Authenticate with username/password to receive JWT access + refresh tokens |

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Refresh Token

| | |
|---|---|
| **Endpoint** | `POST /api/token/refresh/` |
| **Auth** | None |
| **Description** | Exchange a refresh token for a new access token |

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## API Endpoints

### Document Management

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/documents/` | List all documents for the authenticated user | ✅ JWT |
| `POST` | `/api/documents/` | Upload a new PDF document | ✅ JWT |
| `GET` | `/api/documents/{id}/` | Retrieve a specific document | ✅ JWT |
| `PUT` | `/api/documents/{id}/` | Update a document | ✅ JWT |
| `PATCH` | `/api/documents/{id}/` | Partially update a document | ✅ JWT |
| `DELETE` | `/api/documents/{id}/` | Delete a document | ✅ JWT |
| `POST` | `/api/documents/{id}/reprocess/` | Manually trigger re-ingestion | ✅ JWT |

#### Upload Document — `POST /api/documents/`

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Display name for the document |
| `file` | file (PDF) | Yes | The PDF file to upload and index |

**Response (201 Created):**
```json
{
  "id": 1,
  "title": "Machine Learning Textbook.pdf",
  "file": "/media/documents/Machine_Learning_Textbook.pdf",
  "uploaded_at": "2026-03-01T12:00:00Z",
  "processed": true,
  "user": 1
}
```

**Notes:**
- Documents are automatically ingested upon upload (auto-ingestion)
- The `processed` field becomes `true` once vector embeddings are generated
- The `user` field is auto-assigned from the JWT token (read-only)

#### List Documents — `GET /api/documents/`

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "title": "Machine Learning Textbook.pdf",
    "file": "/media/documents/Machine_Learning_Textbook.pdf",
    "uploaded_at": "2026-03-01T12:00:00Z",
    "processed": true,
    "user": 1
  }
]
```

**Multi-tenant isolation:** Users can only see their own documents.

#### Reprocess Document — `POST /api/documents/{id}/reprocess/`

**Response (200 OK):**
```json
{
  "status": "success",
  "document_id": 1,
  "chunks_created": 42,
  "message": "Indexed 42 chunks from 'Machine Learning Textbook.pdf'"
}
```

---

### AI Query (RAG + Verification)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/query/` | Submit a question to the AI verification pipeline | ✅ JWT |

#### Query AI — `POST /api/query/`

**Request Body:**
```json
{
  "query": "What are the three types of machine learning?"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `query` | string | Yes | Max 2000 characters |

**Response (200 OK):**
```json
{
  "answer": "According to the textbook, the three types of machine learning are: 1) Supervised Learning, 2) Unsupervised Learning, and 3) Reinforcement Learning.",
  "faithfulness_score": 0.87,
  "explanation": "Term overlap: 12/15, New terms: 2",
  "source_citation": "Machine Learning Textbook.pdf (Page 12); Machine Learning Textbook.pdf (Page 15)",
  "verification_passed": true,
  "model_used": "gemini",
  "context_chunks_used": 5,
  "metadata": {
    "user_id": 1,
    "query_length": 51
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The AI-generated response grounded in the user's documents |
| `faithfulness_score` | float (0.0–1.0) | Combined confidence score from LLM self-assessment + Critic Agent |
| `explanation` | string | Why this score was assigned (term overlap analysis) |
| `source_citation` | string | Document name(s) and page number(s) referenced |
| `verification_passed` | boolean | `true` if faithfulness ≥ 0.6 threshold |
| `model_used` | string | `gemini`, `groq`, `groq_verification`, or `none` |
| `context_chunks_used` | integer | Number of vector chunks retrieved from pgvector |
| `metadata.user_id` | integer | ID of the authenticated user |
| `metadata.query_length` | integer | Character count of the original query |

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 400 | Missing query | `{"error": "No query provided", "details": "Include 'query' in request body"}` |
| 400 | Query too long | `{"error": "Query too long", "details": "Maximum query length is 2000 characters"}` |
| 401 | Invalid/expired JWT | `{"detail": "Authentication credentials were not provided."}` |

---

### Document Processing

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/process-document/` | Manually trigger document processing | ✅ JWT |

#### Process Document — `POST /api/process-document/`

**Request Body:**
```json
{
  "document_id": 1
}
```

**Response (200 OK):**
```json
{
  "document_id": 1,
  "title": "Machine Learning Textbook.pdf",
  "status": "success",
  "message": "Indexed 42 chunks from 'Machine Learning Textbook.pdf'",
  "chunks_created": 42
}
```

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 400 | Missing document_id | `{"error": "document_id is required"}` |
| 404 | Not found / not owned | `{"error": "Document not found or access denied"}` |

---

### System Telemetry

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/system-insights/` | Retrieve system health and AI metrics | ✅ JWT |

#### System Insights — `GET /api/system-insights/`

**Response (200 OK):**
```json
{
  "status": "Operational",
  "status_details": ["All systems nominal"],
  "metrics": {
    "hallucinations_prevented": 3,
    "failover_recoveries": 1,
    "total_queries": 25,
    "documents_ingested": 8,
    "active_model": "Gemini-1.5-Flash",
    "verification_threshold": 0.6
  },
  "infrastructure": {
    "database": "Connected",
    "vault": "Unsealed",
    "orchestration": "Docker-Compose (Local Cluster)",
    "uptime_score": 100
  }
}
```

**Status Values:**
| Field | Possible Values | Description |
|-------|-----------------|-------------|
| `status` | `Operational`, `Degraded` | Overall system status |
| `infrastructure.database` | `Connected`, `Disconnected` | PostgreSQL connectivity |
| `infrastructure.vault` | `Unsealed`, `Sealed`, `Uninitialized`, `Unreachable` | Vault seal status |
| `metrics.active_model` | `Gemini-1.5-Flash`, `Groq/Llama-3 (Failover Active)` | Currently active LLM |

---

### Health Check

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/health/` | Infrastructure health check (Redis, PostgreSQL, Vault) | ❌ Public |

#### Health Check — `GET /api/health/`

**Response (200 OK — healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-01T12:00:00.000Z",
  "services": {
    "postgresql": {"status": "up", "latency_ms": 2.5},
    "redis": {"status": "up", "latency_ms": 1.1},
    "vault": {"status": "up", "seal_status": "unsealed"}
  }
}
```

**Response (503 — degraded):**
```json
{
  "status": "degraded",
  "timestamp": "2026-03-01T12:00:00.000Z",
  "services": {
    "postgresql": {"status": "up", "latency_ms": 2.5},
    "redis": {"status": "down", "error": "Connection refused"},
    "vault": {"status": "up", "seal_status": "unsealed"}
  }
}
```

---

### Observability

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/metrics` | Prometheus metrics endpoint | ❌ Public |

Returns Prometheus-formatted metrics including all custom VeriRAG counters, histograms, and gauges.

---

### Admin & Schema

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/admin/` | Django admin panel | Session auth |
| `GET` | `/api/schema/` | OpenAPI 3.0 schema (JSON) | ❌ Public |
| `GET` | `/api/schema/swagger-ui/` | Interactive Swagger documentation | ❌ Public |

---

## Error Response Format

All error responses follow a consistent format:

```json
{
  "error": "Short error description",
  "details": "Detailed explanation of what went wrong"
}
```

Or for DRF validation errors:

```json
{
  "field_name": ["Error message for this field"]
}
```

---

## Rate Limiting

Currently not enforced in development. For production, configure DRF throttling in `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/minute',
        'user': '60/minute',
        'query': '20/minute',
    }
}
```
