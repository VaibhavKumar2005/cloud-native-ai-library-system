const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// 🚨 DEMO MODE: Auto-generate a demo token for frontend API requests
// When DEMO_MODE is enabled, create a synthetic token so API calls work
// Backend will ignore token validation and allow any request
// TODO: Remove after May 1st, 2026
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

function generateDemoToken() {
  // Create a simple JWT-like token for demo purposes
  // Backend won't validate this since DEMO_MODE=true disables IsAuthenticated
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({
    token_type: 'access',
    exp: Math.floor(Date.now() / 1000) + 86400 * 365, // 1 year
    user_id: 1,
    demo_mode: true
  }))
  const signature = 'demo_mode_signature'
  return `${header}.${payload}.${signature}`
}

export function consumeOAuthCallbackHash() {
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash

  if (!hash) {
    return null
  }

  const params = new URLSearchParams(hash)
  const oauthStatus = params.get('oauth')
  if (!oauthStatus) {
    return null
  }

  window.history.replaceState(null, '', window.location.pathname + window.location.search)

  if (oauthStatus === 'success') {
    const code = params.get('code')
    if (code) {
      return {
        ok: true,
        provider: params.get('provider'),
        code,
      }
    }

    return {
      ok: false,
      message: 'OAuth login completed without an exchange code. Please try again.',
    }
  }

  return {
    ok: false,
    error: params.get('error'),
    message: params.get('message') || 'OAuth login failed. Please try again.',
  }
}

export function getAccessToken() {
  // In demo mode, generate and return a synthetic token
  if (DEMO_MODE) {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (!token) {
      const demoToken = generateDemoToken()
      localStorage.setItem(ACCESS_TOKEN_KEY, demoToken)
      return demoToken
    }
    return token
  }
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function storeSession(accessToken, refreshToken) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function isAuthenticated() {
  // In demo mode, always consider user authenticated
  if (DEMO_MODE) {
    return true
  }
  return Boolean(getAccessToken())
}
