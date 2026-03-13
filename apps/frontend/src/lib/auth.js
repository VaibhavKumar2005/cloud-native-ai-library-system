const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

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
  return Boolean(getAccessToken())
}
