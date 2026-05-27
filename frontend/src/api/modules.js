import api from './index'

export const auth = {
  register: (username, password) => api.post('/auth/register', { username, password }),
  login: (username, password) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
}

export const chat = {
  send: (message, userId = 'default_user', sessionId = 'default') =>
    api.post('/chat', { message, user_id: userId, session_id: sessionId }),
}

export const rag = {
  query: (query, userId = 'default_user', topK = 5, useHyde = true) =>
    api.post('/rag/query', { query, user_id: userId, top_k: topK, use_hyde: useHyde }),
}

export const knowledge = {
  list: (userId) => api.get('/knowledge/list', { params: { user_id: userId } }),
  search: (query, k = 5, userId) => api.get('/knowledge/search', { params: { query, k, user_id: userId } }),
  upload: (file, userId = 'default_user') => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/knowledge/upload?user_id=${userId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (filename, userId = 'default_user') =>
    api.delete(`/knowledge/delete/${filename}`, { params: { user_id: userId } }),
}

export const audit = {
  logs: (params = {}) => api.get('/audit/logs', { params }),
}

export const health = {
  check: () => api.get('/health'),
}