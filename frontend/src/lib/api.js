/**
 * VeriRAG API Client — Axios instance with automatic JWT token refresh.
 *
 * Every request attaches the stored access_token.
 * On a 401, it tries to refresh once using the refresh_token.
 * If refresh also fails, the user is redirected to /login.
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach Bearer token ─────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor: auto-refresh on 401 ───────────────────────
let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If not a 401 or already retried, reject immediately
    if (!error.response || error.response.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // If we're already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      isRefreshing = false
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    try {
      const { data } = await axios.post(`${API_BASE}/api/token/refresh/`, {
        refresh: refreshToken,
      })

      localStorage.setItem('access_token', data.access)
      if (data.refresh) {
        localStorage.setItem('refresh_token', data.refresh)
      }

      processQueue(null, data.access)

      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default api
