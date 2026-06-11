import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60_000,
})

// Request interceptor — log in dev
api.interceptors.request.use(config => {
  if (import.meta.env.DEV) {
    console.log(`→ ${config.method?.toUpperCase()} ${config.url}`)
  }
  return config
})

// Response interceptor — normalise errors
api.interceptors.response.use(
  res => res,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(msg))
  },
)

// ── Namespaced API objects ─────────────────────────────────────────────────────

export const investigateAPI = {
  start:           (data)  => api.post('/investigate', data),
  status:          (id)    => api.get(`/investigate/${id}/status`),
  report:          (id)    => api.get(`/investigate/${id}`),
  downloadMarkdown:(id)    => api.get(`/investigate/${id}/report/markdown`, { responseType: 'blob' }),
  testFoundry:     ()      => api.get('/investigate/test-foundry'),
}

export const watchlistAPI = {
  list:   ()     => api.get('/watchlist'),
  add:    (data) => api.post('/watchlist', data),
  remove: (id)   => api.delete(`/watchlist/${id}`),
}

export const reportAPI = {
  markdown: (id) => api.get(`/report/${id}/markdown`),
}

// ── Legacy function exports (keep existing callers working) ────────────────────

export const startInvestigation        = (data) => investigateAPI.start(data)
export const getInvestigationStatus    = (id)   => investigateAPI.status(id)
export const getInvestigationReport    = (id)   => investigateAPI.report(id)

export default api
