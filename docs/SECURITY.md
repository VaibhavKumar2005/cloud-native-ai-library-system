# 🔐 VeriRAG Security Model

> How VeriRAG secures API keys, authenticates users, and isolates multi-tenant data.

---

## Overview

VeriRAG implements a **defense-in-depth** security architecture across four layers:

1. **Secret Management** — HashiCorp Vault for dynamic API key retrieval
2. **Authentication** — JWT tokens via Django SimpleJWT
3. **Authorization** — Multi-tenant data isolation at the ORM + vector store level
4. **Transport Security** — Content Security Policy (CSP) headers + CORS controls

---

## 1. HashiCorp Vault Integration

### Why Vault?

Instead of storing API keys in environment variables or `.env` files, VeriRAG retrieves secrets **dynamically at runtime** from HashiCorp Vault. This provides:

- **Centralized secret management** — Single source of truth for all API keys
- **Audit logging** — Every secret access is logged
- **Dynamic rotation** — Keys can be rotated without redeploying
- **Caching** — 5-minute TTL cache reduces Vault round-trips

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Django App  │────▶│  hvac Client │────▶│ HashiCorp    │
│ rag_logic.py│     │  (Python)    │     │ Vault        │
└─────────────┘     └──────────────┘     │              │
                                         │ KV v2 Engine │
                                         │ secret/myapp │
                                         └──────────────┘
```

### Secrets Stored in Vault

| Secret Path | Key | Description |
|-------------|-----|-------------|
| `secret/myapp` | `GOOGLE_API_KEY` | Google Gemini + Embeddings API key |
| `secret/myapp` | `GROQ_API_KEY` | Groq/Llama-3 fallback API key |
| `secret/myapp` | `DB_NAME` | Database name |
| `secret/myapp` | `DB_USER` | Database username |
| `secret/myapp` | `DB_PASSWORD` | Database password |
| `secret/myapp` | `DB_HOST` | Database host |
| `secret/myapp` | `DB_PORT` | Database port |

### How It Works

The `get_api_key_from_vault()` function in [rag_logic.py](../apps/backend/ai_engine/rag_logic.py) implements the retrieval logic:

```python
def get_api_key_from_vault(key_name="GOOGLE_API_KEY"):
    """
    1. Check in-memory cache (TTL: 5 minutes)
    2. Connect to Vault using VAULT_ADDR and VAULT_TOKEN env vars
    3. Authenticate via token
    4. Read from KV v2 at secret/myapp
    5. Cache the result and return
    6. On ANY failure → fall back to environment variable
    """
```

**Fallback behavior:** If Vault is unreachable, sealed, or the token is invalid, the system gracefully falls back to reading from environment variables. This ensures the application remains functional during Vault maintenance.

### Caching Strategy

```python
_api_key_cache = {"key": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutes

# On each request:
# 1. Check if cache entry exists and is < 5 minutes old
# 2. If valid, return cached key (no Vault round-trip)
# 3. If expired, fetch from Vault and update cache
```

This reduces Vault API calls from once-per-request to once-per-5-minutes.

### Vault Setup (Development)

In Docker Compose, Vault runs in **dev mode**:

```yaml
rag-vault:
  image: vault:1.13.3
  environment:
    VAULT_DEV_ROOT_TOKEN_ID: "${VAULT_TOKEN:-root}"
    VAULT_ADDR: "http://0.0.0.0:8200"
  cap_add:
    - IPC_LOCK
```

Dev mode automatically:
- Initializes Vault
- Unseals it
- Sets the root token to `root`
- Enables an in-memory storage backend

### Vault Setup (Production)

For production, use the `scripts/setup/init_vault.ps1` script which:

1. Initializes Vault with Shamir's Secret Sharing (`key-shares=1, key-threshold=1`)
2. Saves unseal keys and root token to `vault_keys.txt`
3. Unseals Vault
4. Enables the KV v2 secrets engine at `secret/`
5. Injects API keys into `secret/myapp`

**Critical:** In production, never use dev mode. Configure:
- TLS with a proper certificate
- A durable storage backend (Consul, PostgreSQL, or Azure Key Vault)
- Multiple unseal keys with a higher threshold
- Audit logging enabled

---

## 2. JWT Authentication (SimpleJWT)

### Token Flow

```
┌────────┐   POST /api/token/    ┌──────────┐
│ Client │──────────────────────▶│  Django  │
│        │   {user, password}    │ SimpleJWT│
│        │◀──────────────────────│          │
│        │   {access, refresh}   └──────────┘
│        │
│        │   GET /api/documents/
│        │──────────────────────▶  Authorization: Bearer <access>
│        │                        ──▶ JWTAuthentication validates
│        │◀──────────────────────  200 OK + data
│        │
│        │   POST /api/token/refresh/
│        │──────────────────────▶  {refresh: "..."}
│        │◀──────────────────────  {access: "new_token"}
└────────┘
```

### Configuration

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}
```

All API endpoints require authentication by default. Only the health check endpoint overrides this with `AllowAny`.

### Frontend Token Management

The React frontend stores tokens in `localStorage`:

```javascript
// Login
const res = await axios.post('/api/token/', { username, password });
localStorage.setItem('access_token', res.data.access);
localStorage.setItem('refresh_token', res.data.refresh);

// Authenticated request
const token = localStorage.getItem('access_token');
axios.get('/api/documents/', {
  headers: { Authorization: `Bearer ${token}` }
});
```

---

## 3. Multi-Tenant Data Isolation

### ORM-Level Isolation

Every document is associated with a user via a ForeignKey:

```python
class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
```

The `DocumentViewSet` enforces isolation in the queryset:

```python
def get_queryset(self):
    return Document.objects.filter(user=self.request.user)
```

### Vector Store Isolation

When documents are ingested, each chunk is tagged with the user's ID:

```python
chunk.metadata["user_id"] = str(doc.user.id)
```

During similarity search, the filter ensures cross-tenant isolation:

```python
docs = vector_db.similarity_search(
    query, k=5,
    filter={"user_id": str(user_id)}
)
```

This means User A's documents are **never** returned in User B's queries, even at the vector embedding level.

---

## 4. Content Security Policy (CSP)

VeriRAG implements CSP headers via `django-csp`:

```python
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'connect-src': ("'self'", 'http://localhost:8000'),
        'script-src': ("'self'",),
        'style-src': ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'),
        'font-src': ("'self'", 'https://fonts.gstatic.com'),
        'img-src': ("'self'", 'data:', 'blob:'),
    }
}
```

This prevents:
- **XSS attacks** — Only scripts from the same origin are allowed
- **Data exfiltration** — `connect-src` restricts API call destinations
- **Clickjacking** — `X-Frame-Options` middleware (Django default)

---

## 5. CORS Configuration

```python
# Development: Allow all origins
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Production: Whitelist specific origins
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        host.strip() for host in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    ]
```

---

## 6. Security Best Practices Checklist

| Practice | Status | Implementation |
|----------|--------|----------------|
| Secrets in Vault (not env vars) | ✅ | `get_api_key_from_vault()` with 5-min cache |
| JWT authentication | ✅ | SimpleJWT with access + refresh tokens |
| Multi-tenant isolation | ✅ | ORM filter + pgvector metadata filter |
| CSP headers | ✅ | `django-csp` middleware |
| CORS restrictions | ✅ | Whitelist in production |
| SQL injection prevention | ✅ | Django ORM (parameterized queries) |
| CSRF protection | ✅ | Django CSRF middleware (API uses JWT) |
| Secret key generation | ✅ | `secrets.token_urlsafe(50)` in dev, mandatory env var in prod |
| Debug mode check | ✅ | Raises `ValueError` if SECRET_KEY missing in prod |
| Password hashing | ✅ | Django's default PBKDF2 |

---

## Security Cleanup Scripts

The repository includes cleanup scripts to remove accidental secret exposure:

- `scripts/security/security-cleanup.sh` (Linux/macOS)
- `scripts/security/security-cleanup.ps1` (Windows/PowerShell)

These scripts scan for and remove hardcoded API keys, tokens, and passwords from the codebase.
