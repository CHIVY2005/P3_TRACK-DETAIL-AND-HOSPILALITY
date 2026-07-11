export const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || 'http://127.0.0.1:8001'

export const API_BASE_URL = `${API_ORIGIN.replace(/\/$/, '')}/api/v1`
