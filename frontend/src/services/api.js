import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/api/v1/auth/login', credentials),
  register: (userData) => api.post('/api/v1/auth/register', userData),
  getCurrentUser: () => api.get('/api/v1/auth/me'),
};

// Portfolio API
export const portfolioAPI = {
  list: () => api.get('/api/v1/portfolios'),
  get: (id) => api.get(`/api/v1/portfolios/${id}`),
  create: (data) => api.post('/api/v1/portfolios', data),
  update: (id, data) => api.put(`/api/v1/portfolios/${id}`, data),
  delete: (id) => api.delete(`/api/v1/portfolios/${id}`),
  getMetrics: (id) => api.get(`/api/v1/portfolios/${id}/metrics`),
  getRiskMetrics: (id) => api.get(`/api/v1/portfolios/${id}/risk`),
};

// Chat API
export const chatAPI = {
  createSession: (data) => api.post('/api/v1/chat/sessions', data),
  getSession: (sessionId) => api.get(`/api/v1/chat/sessions/${sessionId}`),
  sendMessage: (sessionId, message) =>
    api.post(`/api/v1/chat/sessions/${sessionId}/messages`, message),
  deleteSession: (sessionId) => api.delete(`/api/v1/chat/sessions/${sessionId}`),

  // SSE streaming endpoint (returns URL)
  getStreamURL: (sessionId) =>
    `${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/messages`,
};

export default api;
