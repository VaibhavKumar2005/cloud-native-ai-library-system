# Frontend Authentication Flows & Architecture

This document provides a comprehensive guide to the VeriRAG frontend authentication system, covering user flows, architecture, and implementation details.

## System Overview

VeriRAG implements a **multi-method authentication system** with three primary flows:

1. **Password-Based Authentication**: Traditional username/password login
2. **Magic Link Authentication**: Passwordless email-based sign-in (Enterprise feature)
3. **OAuth2 Social Login**: Google and GitHub authentication

All methods result in the same JWT-based session structure, allowing seamless switching between auth providers.

---

## Authentication Architecture

### Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│                         App.jsx                              │
│                      (Route Container)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                                 │
        ▼                                 ▼
    ┌─────────────┐                ┌──────────┐
    │   Login.jsx │                │ Dashboard│
    │             │                │          │
    │  - Tabs     │                │ (Auth'd) │
    │  - Password │                │          │
    │  - Email    │                └──────────┘
    │  - OAuth    │
    └─────────────┘
        │   │
        │   └─────────────────┐
        │                     │
        ▼                     ▼
    ┌──────────────────┐  ┌──────────────┐
    │EmailAuthTab.jsx  │  │OAuth handlers │
    │ (passwordless)   │  │(Google/GH)    │
    └──────────────────┘  └──────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `Login.jsx` | Main login page, tab navigation |
| `EmailAuthTab.jsx` | Passwordless magic link UI |
| `lib/auth.js` | Auth utility functions (token storage, session management) |
| `lib/api.js` | API client with JWT auto-injection |
| `lib/colors.js` | Color system (design tokens) |
| `components/ui/badge.jsx` | Status indicators, tags |
| `components/ui/alert.jsx` | Error/success messages |
| `components/ui/tabs.jsx` | Tab navigation component |

---

## User Flows

### Flow 1: Password-Based Login

```
User                      Frontend                    Backend
  │                           │                          │
  ├─────────────────────────>│ Enter username/password   │
  │                           │                          │
  │                           ├──────────────────────────>│
  │                           │ POST /api/token/          │
  │                           │ {username, password}      │
  │<──────────────────────────┤ 200 OK                    │
  │                           │<──────────────────────────┤
  │                           │ {access, refresh}         │
  │                           │                          │
  ├─ Redirect to Dashboard ──>│                          │
  │ (session saved)          │                          │
  │                           │                          │

✅ Result: User authenticated, JWT tokens stored in localStorage
```

**Endpoint**: `POST /api/token/`
**Payload**: `{ "username": "user", "password": "pass" }`
**Response**: `{ "access": "jwt...", "refresh": "jwt..." }`

---

### Flow 2: Magic Link (Passwordless Email Auth)

```
User                      Frontend                    Backend
  │                           │                          │
  ├─ Switch to Email Tab ────>│                          │
  ├─ Enter email ────────────>│                          │
  ├─ Click "Send Magic Link" ─>│                          │
  │                           │                          │
  │                           ├──────────────────────────>│
  │                           │ POST /api/auth/email/send/│
  │                           │ {email}                   │
  │                           │                          │
  │                           │<──────────────────────────┤
  │<──────────────────────────┤ {status: "link_sent"}     │
  │                           │                          │
  │ 📧 Receives email with    │                          │
  │    magic link token       │                          │
  │                           │                          │
  ├─ Clicks link ────────────>│                          │
  │  /login?email_token=...   │                          │
  │                           │                          │
  │                           ├──────────────────────────>│
  │                           │ POST /api/auth/email/verify│
  │                           │ {token}                   │
  │                           │                          │
  │                           │<──────────────────────────┤
  │<──────────────────────────┤ {access, refresh}         │
  │                           │                          │
  ├─ Redirect to Dashboard ──>│                          │
  │ (session auto-saved)     │                          │
  │                           │                          │

✅ Result: User authenticated via email, no password needed
```

**Endpoints**:
- **Send**: `POST /api/auth/email/send/` → `{email}`
- **Verify**: `POST /api/auth/email/verify/` → `{token}`

**Key Benefits**:
- ✅ No password to remember
- ✅ Enterprise security standard
- ✅ Mobile-friendly (one-click email link)
- ✅ New users auto-created on first link verification

---

### Flow 3: OAuth2 Social Login (Google/GitHub)

```
User                      Frontend                    Backend                    Provider
  │                           │                          │                          │
  ├─ Click "Continue with ──>│                          │                          │
  │  Google/GitHub"          │                          │                          │
  │                           │                          │                          │
  │                           ├──────────────────────────>│ GET /api/auth/          │
  │                           │ /google/start/ or         │ google/start/            │
  │                           │ /github/start/            │                         │
  │                           │                          │                         │
  │                           │<──────────────────────────┤ Redirect to provider   │
  │<──────────────────────────┤ oauth consent screen URL  │                        │
  │                           │                          │                         │
  ├─────────────────────────────────────────────────────────────────────────────────>│
  │                           │                          │                         │
  │                                              [User grants permission]            │
  │                           │                          │                         │
  │<────────────────────────────────────────────────────────────────────────────────┤
  │ Redirect with auth code   │                          │                         │
  │ /login#oauth=success&code=...
  │                           │                          │                         │
  ├─────────────────────────>│                          │                         │
  │                           │                          │                         │
  │                           ├──────────────────────────>│ POST /api/auth/exchange/│
  │                           │ POST /api/auth/exchange/ │ {code}                  │
  │                           │ {code}                   │                         │
  │                           │                          ├───────────────────────> │
  │                           │                          │ [Provider validation]   │
  │                           │                          │<─────────────────────── │
  │                           │                          │ user info               │
  │                           │                          │                         │
  │                           │<──────────────────────────┤ {access, refresh}      │
  │<──────────────────────────┤                          │                         │
  │                           │                          │                         │
  ├─ Redirect to Dashboard ──>│                          │                         │
  │                           │                          │                         │

✅ Result: User authenticated via OAuth, JWT tokens stored
```

**Endpoints**:
- **Initiate**: `GET /api/auth/google/start/` or `/api/auth/github/start/`
- **Callback**: `GET /api/auth/google/callback/` or `/api/auth/github/callback/`
- **Exchange**: `POST /api/auth/exchange/` → `{code}`

**Key Features**:
- ✅ Secure OAuth2 code exchange (not token in URL)
- ✅ Automatic user creation for new social accounts
- ✅ Account linking for existing users
- ✅ Email validation required

---

## Token Management

### JWT Token Structure

All authentication methods result in two JWT tokens:

```javascript
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| Token | Lifetime | Use Case |
|-------|----------|----------|
| `access` | 2 hours | API request authentication |
| `refresh` | 7 days | Obtain new access token when expired |

### Token Storage

Tokens are stored in **localStorage** (client-side):

```javascript
// Auto-saved by auth.js storeSession()
localStorage.setItem('access_token', token)
localStorage.setItem('refresh_token', token)
```

### Auto-Refresh Mechanism

When access token expires:

1. Frontend detects 401 Unauthorized
2. Automatically refreshes using `refresh_token`
3. Updates `access_token` in storage
4. Retries original request
5. If refresh fails → redirect to `/login`

**Implementation**: `lib/api.js` handles this transparently

---

## Security Features

### CSRF Protection

- ✅ Django CSRF tokens embedded in forms
- ✅ Safe SameSite cookies
- ✅ Token rotation on refresh

### OAuth Security

- ✅ **Authorization Code Flow** (not implicit token flow)
- ✅ **State parameter** validation (CSRF for OAuth)
- ✅ **Code verification** server-side (token exchange)
- ✅ **Email verification** required (Google/GitHub)

### Email Authentication Security

- ✅ **One-time use**: Token consumed immediately after use
- ✅ **TTL**: 15-minute expiration
- ✅ **Hashing**: Token stored as SHA256 hash (never raw)
- ✅ **No email leakage**: No confirmation that email exists

### Session Security (All Methods)

- ✅ `HttpOnly` cookies (JavaScript can't access)
- ✅ `Secure` flag (HTTPS only)
- ✅ `SameSite=Strict` (CSRF prevention)
- ✅ Token rotation on refresh
- ✅ Automatic logout on tab close (refresh fails)

---

## UI Component Usage

### Login Page Structure

```jsx
<Login>
  ├─ Tabs (Password | Magic Link)
  ├─ Tab 1: Password Form
  │  ├─ Username Input
  │  ├─ Password Input
  │  └─ Sign In Button
  │
  ├─ Tab 2: Email Form
  │  ├─ EmailAuthTab component
  │  │  ├─ Email Input
  │  │  ├─ Send Magic Link Button
  │  │  └─ Success Message
  │  │
  │  └─ Error Handler
  │
  ├─ Divider ("Or continue with")
  │
  └─ Social Auth Buttons
     ├─ Google Button
     └─ GitHub Button
```

### Badge Component (Status Indicators)

```jsx
<Badge variant="success">Authenticated</Badge>
<Badge variant="warning">Session Expiring</Badge>
<Badge variant="error">Auth Failed</Badge>
<Badge variant="info">Verifying...</Badge>
```

### Alert Component (Messages)

```jsx
<Alert variant="success" title="Login Successful">
  You are now signed in
</Alert>

<Alert variant="error" title="Invalid Credentials">
  Check your username and password
</Alert>
```

---

## Error Handling

### Common Error Scenarios

| Error | HTTP Status | Recovery |
|-------|------------|----------|
| Invalid credentials | 401 | Show error, retry login |
| Token expired | 401 | Auto-refresh, retry |
| Refresh failed | 401 | Clear session, redirect to login |
| Network error | - | Show error, allow retry |
| OAuth cancelled | - | Show message, allow retry |
| Email doesn't exist | 400 | Create user on first auth |
| OAuth account mismatch | 400 | Show account linking prompt |

### Error Display

All errors displayed using the `Alert` component:

```jsx
{error && (
  <Alert variant="error" onClose={() => setError(null)}>
    {error}
  </Alert>
)}
```

---

## Mobile Responsiveness

### Responsive Design

- ✅ Mobile-first approach
- ✅ Single-column layout on mobile
- ✅ Touch-friendly button sizes (min 44px)
- ✅ Readable font sizes (min 16px on mobile)
- ✅ Sufficient spacing between tap targets

### Magic Link on Mobile

The magic link flow is **mobile-optimized**:

```
1. User receives email on phone
2. Taps magic link in email client
3. Opens webpage, auto-verifies token
4. Redirects to app dashboard
5. Session persists across all devices
```

**No popup windows or complex flows needed!**

---

## Configuration

### Environment Variables

```javascript
// apps/frontend/.env.local
VITE_API_URL=http://localhost:8000  # Backend URL
VITE_GOOGLE_CLIENT_ID=xxx           # For client-side validation
VITE_GITHUB_CLIENT_ID=xxx           # For client-side validation
```

### Backend Configuration (settings.py)

```python
# OAuth Redirect URIs must match frontend flow
GOOGLE_OAUTH_REDIRECT_URI = "https://app.verirag.com/api/auth/google/callback/"
GITHUB_OAUTH_REDIRECT_URI = "https://app.verirag.com/api/auth/github/callback/"

# CORS must allow frontend origin
CORS_ALLOWED_ORIGINS = [
    "https://app.verirag.com",
    "http://localhost:5173",  # Dev
]

# CSRF must trust frontend
CSRF_TRUSTED_ORIGINS = [
    "https://app.verirag.com",
    "http://localhost:5173",
]
```

---

## Testing the Flows

### Local Development

#### 1. Test Password Login
```bash
# Credentials from admin user
Username: admin
Password: (from dev setup)
```

#### 2. Test Email Magic Link
```bash
# Go to login page
# Click "Magic Link" tab
# Enter any email
# Check console (DEBUG=True shows link)
# Ctrl+F in console for "Magic link generated"
# Copy token from URL
# Paste in browser frontend
```

#### 3. Test OAuth (Google)
```bash
# Must have Google OAuth app configured
# Credentials in .env
# Click "Continue with Google"
# Browser redirects to Google
# You authorize
# Redirected back with auth code
```

### Production Testing (ACA)

```bash
# Health check endpoint
curl https://api.example.com/api/health/

# Detailed health check (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/api/health/details/
```

---

## Performance Considerations

### Load Time Optimization

- ✅ Lazy load components (code splitting)
- ✅ Minify bundles
- ✅ Cache HTTP requests
- ✅ Use CDN for static assets

### Token Refresh Guidelines

- ✅ Refresh **before** expiration if activity detected
- ✅ Refresh **silently** without user interaction
- ✅ Cache refresh tokens in IndexedDB for multi-tab sync
- ✅ Clear tokens on logout (all tabs)

---

## Future Enhancements

### TIER 2 Features

- 🔲 WebSocket for real-time auth events
- 🔲 Biometric authentication (WebAuthn)
- 🔲 Multi-factor authentication (MFA)
- 🔲 Session management dashboard (revoke tokens)
- 🔲 Account linking UI (connect multiple providers)
- 🔲 Actual email service integration (Resend/Postmark)
- 🔲 Single Sign-On (SSO) with corporate IdP

### TIER 3 Features

- 🔲 Passwordless phone number authentication
- 🔲 Push notifications for login approval
- 🔲 Zero-knowledge proofs for state management
- 🔲 Decentralized identity (DID) support

---

## Troubleshooting

### "Cannot POST /api/token/"
- Check backend is running: `docker-compose ps`
- Verify VITE_API_URL in .env.local
- Check CORS configuration in Django settings

### "OAuth callback URL mismatch"
- Ensure OAuth app redirect URI matches exactly
- Check for trailing slashes
- Verify port numbers in non-prod environments

### "Token expired, not refreshing"
- Check localStorage for `refresh_token`
- Verify refresh endpoint is accessible
- Check backend token validation logic

### "Email link not working"
- Check 15-minute TTL hasn't expired
- Verify email token is URL-encoded properly
- Ensure FRONTEND_URL in backend settings matches

---

## References

- [OAuth 2.0 Authorization Code Flow](https://datatracker.ietf.org/html/rfc6749#section-1.3.1)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Django REST Framework JWT Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)

---

## Support

For authentication issues:
1. Check browser console for errors
2. Use `curl` to test API endpoints directly
3. Review backend health check: `/api/health/details/`
4. Check server logs: `docker-compose logs rag-backend`
