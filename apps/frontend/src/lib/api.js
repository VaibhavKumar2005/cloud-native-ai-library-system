/**
 * VeriRAG API Client for demo mode.
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
})

api.interceptors.request.use(
  (config) => {
    // Let the browser attach the multipart boundary for file uploads.
    if (config.data instanceof FormData && config.headers) {
      delete config.headers['Content-Type']
    } else if (config.headers && !config.headers['Content-Type']) {
      config.headers['Content-Type'] = 'application/json'
    }

    return config
  },
  (error) => Promise.reject(error)
)

export default api
