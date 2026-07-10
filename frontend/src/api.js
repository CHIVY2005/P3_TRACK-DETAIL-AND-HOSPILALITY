const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || 'http://localhost:8001'

export const API_BASE_URL = `${API_ORIGIN.replace(/\/$/, '')}/api/v1`
