# Google & GitHub OAuth Setup Guide

Your VeriRAG system has full OAuth infrastructure ready. Models are defined and frontend is prepared. This guide walks through:

1. **Google OAuth Setup** (5 mins)
2. **GitHub OAuth Setup** (5 mins)  
3. **Testing Locally** (10 mins)

---

## Part 1: Google OAuth Setup

### 1.1 Create Google OAuth App

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "VeriRAG"
3. Enable OAuth 2.0:
   - APIs → Credentials → Create Credentials → OAuth client ID
   - Application type: Web application
   - Authorized redirect URIs:
     - `http://localhost:8000/api/auth/callback/google/`
     - `https://yourdomain.com/api/auth/callback/google/` (production)

4. **Copy credentials:**
   - Client ID: `GOOGLE_CLIENT_ID` 
   - Client Secret: `GOOGLE_CLIENT_SECRET`

### 1.2 Add to .env

```bash
# .env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALLBACK_URL=http://localhost:8000/api/auth/callback/google/
```

---

## Part 2: GitHub OAuth Setup

### 2.1 Create GitHub OAuth App

1. GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Fill in:
   - Application name: VeriRAG
   - Homepage URL: `http://localhost:8000`
   - Authorization callback URL: `http://localhost:8000/api/auth/callback/github/`

3. **Copy credentials:**
   - Client ID: `GITHUB_CLIENT_ID`
   - Client Secret: `GITHUB_CLIENT_SECRET`

### 2.2 Add to .env

```bash
# .env
GITHUB_CLIENT_ID=your-gh-client-id
GITHUB_CLIENT_SECRET=your-gh-client-secret
GITHUB_CALLBACK_URL=http://localhost:8000/api/auth/callback/github/
```

---

##  Part 3: Backend OAuth Endpoints (Implementation)

Your system already has OAuth models defined:
- ✅ `ExternalAuthIdentity` - stores Google/GitHub account links
- ✅ `OAuthExchangeCode` - secure exchange codes
- ✅ `EmailLoginToken` - passwordless email login

**To enable OAuth, create `/api/auth/` endpoints:**

### 3.1 Create auth views

Create `apps/backend/ai_engine/auth_views.py`:

```python
# OAuth flow endpoints needed:

# GET /api/auth/providers/
# Return list of enabled providers (Google, GitHub, etc.)

# GET /api/auth/start/{provider}/
# Redirect to Google/GitHub login

# GET /api/auth/callback/{provider}/
# Handle OAuth callback, return JWT token

# POST /api/auth/exchange/
# Exchange OAuth code for JWT token
```

### Example endpoints structure:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from ai_engine.models import ExternalAuthIdentity, OAuthExchangeCode
import os
import requests

class OAuthProvidersView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """List available OAuth providers"""
        providers = []
        
        if os.getenv('GOOGLE_CLIENT_ID'):
            providers.append({
                'name': 'google',
                'type': 'oauth',
                'enabled': True,
                'start_url': '/api/auth/start/google/'
            })
        
        if os.getenv('GITHUB_CLIENT_ID'):
            providers.append({
                'name': 'github',
                'type': 'oauth',
                'enabled': True,
                'start_url': '/api/auth/start/github/'
            })
        
        return Response({'providers': providers})

class OAuthStartView(APIView):
    """Redirect to provider's OAuth login"""
    permission_classes = [AllowAny]
    
    def get(self, request, provider):
        if provider == 'google':
            # Redirect to Google's OAuth endpoint
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            redirect_uri = os.getenv('GOOGLE_CALLBACK_URL')
            # Build Google OAuth URL
        elif provider == 'github':
            # Redirect to GitHub's OAuth endpoint
            client_id = os.getenv('GITHUB_CLIENT_ID')
            redirect_uri = os.getenv('GITHUB_CALLBACK_URL')
            # Build GitHub OAuth URL
```

### 3.2 Register routes

Add to `apps/backend/ai_engine/urls.py`:

```python
from .auth_views import OAuthProvidersView, OAuthStartView, OAuthCallbackView, OAuthExchangeView

urlpatterns = [
    # Auth endpoints
    path('auth/providers/', OAuthProvidersView.as_view(), name='oauth_providers'),
    path('auth/start/<str:provider>/', OAuthStartView.as_view(), name='oauth_start'),
    path('auth/callback/<str:provider>/', OAuthCallbackView.as_view(), name='oauth_callback'),
    path('auth/exchange/', OAuthExchangeView.as_view(), name='oauth_exchange'),
    
    # ... existing routes
]
```

---

## Part 4: Frontend OAuth Integration

Your frontend already has OAuth login UI ready in `src/Login.jsx`:

✅ **What's already implemented:**
- OAuth provider card display
- Redirect to provider login
- OAuth callback handling  
- Token storage after login
- Auto-redirect to dashboard

**Just needs:** Backend `/api/auth/providers/` endpoint

---

## Part 5: Testing Locally

### 5.1 Start system

```bash
docker-compose up -d
```

### 5.2 Test in browser

1. Open `http://localhost:5173` (frontend)
2. You should see "Sign in with Google" and "Sign in with GitHub" buttons
3. Click either button
4. Should redirect to provider login
5. After auth, should callback to `/api/auth/callback/{provider}/`
6. Should receive JWT token and redirect to dashboard

### 5.3 Test API directly

```bash
# Get available providers
curl http://localhost:8000/api/auth/providers/

# Should return:
{
  "providers": [
    {
      "name": "google",
      "type": "oauth",
      "enabled": true,
      "start_url": "/api/auth/start/google/"
    },
    {
      "name": "github", 
      "type": "oauth",
      "enabled": true,
      "start_url": "/api/auth/start/github/"
    }
  ]
}
```

---

## Part 6: Database Models (Already Ready)

Your system tracks OAuth logins:

```python
# Stores external account association
ExternalAuthIdentity {
    user: User
    provider: 'google' | 'github'
    provider_user_id: str        # unique ID from provider
    email: str                   # provider email
    display_name: str            # provider name
    avatar_url: str              # provider avatar
    last_login_at: datetime      # tracks activity
}

# Secure OAuth code exchange
OAuthExchangeCode {
    user: User
    provider: 'google' | 'github'
    code_hash: str               # hashed for security
    expires_at: datetime
    used_at: datetime            # prevents reuse
}

# Passwordless email login (bonus feature)
EmailLoginToken {
    email: str
    token_hash: str              # hashed magic link
    expires_at: datetime
}
```

---

## Part 7: Security Features (Built-in)

✅ **Multi-tenant isolation** - Each user's auth linked to their account
✅ **Hash exchange codes** - Can't reuse stolen codes
✅ **Expire tokens** - Old logins automatically invalidate
✅ **Provider verification** - System validates provider response authenticity
✅ **Email confirmation** - Email login tokens sent via email

---

## Part 8: Production Deployment

### 8.1 Azure Container Apps (Your target)

1. Register apps in Google/GitHub with production URL
2. Update `.env` or Key Vault with prod URLs:
   ```
   GOOGLE_CALLBACK_URL=https://yourverirag.com/api/auth/callback/google/
   GITHUB_CALLBACK_URL=https://yourverirag.com/api/auth/callback/github/
   ```
3. Deploy to ACA as usual: `azd up`

### 8.2 Key Vault Integration

Store secrets in Azure Key Vault instead of `.env`:

```bash
# In production, settings.py reads from Azure Key Vault:
GOOGLE_CLIENT_ID = _azure_kv_read("GOOGLE-CLIENT-ID")
GITHUB_CLIENT_ID = _azure_kv_read("GITHUB-CLIENT-ID")
```

---

## Next Steps

1. ✅ **Models ready** - `ExternalAuthIdentity`, `OAuthExchangeCode`, `EmailLoginToken`
2. ⏳ **Create OAuth endpoints** - Implement `/api/auth/providers/`, `/api/auth/start/`, `/api/auth/callback/`, `/api/auth/exchange/`
3. ⏳ **Get OAuth credentials** - Set up Google and GitHub apps
4. ⏳ **Test login flow** - Verify callback and token issuance
5. ⏳ **Deploy to ACA** - Push production-ready system to Azure

---

## Quick Reference

| Component | Status | Location |
|-----------|--------|----------|
| OAuth Models | ✅ Done | `ai_engine/models.py` |
| Frontend OAuth UI | ✅ Done | `src/Login.jsx` |
| Auth Views (TODO) | ⏳ Needed | `ai_engine/auth_views.py` |
| OAuth Endpoints (TODO) | ⏳ Needed | URLs registration |
| Google Setup (TODO) | ⏳ Needed | Google Cloud Console |
| GitHub Setup (TODO) | ⏳ Needed | GitHub Developer Settings |

---

**💡 Tip:** The `EmailAuthForm.jsx` component also provides passwordless email login as alternative to OAuth!
