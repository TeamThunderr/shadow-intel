import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

export const startInvestigation = (data) => api.post('/investigate', data)
export const getInvestigationStatus = (entityId) => api.get(`/investigate/${entityId}/status`)
export const getInvestigationReport = (entityId) => api.get(`/investigate/${entityId}`)
export const getWatchlist = () => api.get('/watchlist')
export const addToWatchlist = (data) => api.post('/watchlist', data)
export const removeFromWatchlist = (entityId) => api.delete(`/watchlist/${entityId}`)
export const downloadMarkdown = (entityId) => api.get(`/report/${entityId}/markdown`)

export default api
