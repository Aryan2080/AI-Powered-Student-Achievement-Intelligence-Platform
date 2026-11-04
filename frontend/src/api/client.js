/**
 * frontend/src/api/client.js
 * Centralized API client service with automatic bearer token attachment.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const api = {
  // Auth
  login: (email, password) => apiClient.post('/auth/login', { email, password }),
  register: (payload) => apiClient.post('/auth/register', payload),
  getMe: () => apiClient.get('/auth/me'),

  // Students
  getStudentProfile: (studentId) => apiClient.get(`/students/profile/${studentId}`),
  updateStudentProfile: (studentId, payload) => apiClient.patch(`/students/${studentId}`, payload),

  // Achievements
  submitAchievement: (payload) => apiClient.post('/achievements', payload),
  getStudentAchievements: (studentId, status = null) => {
    const params = status ? { status } : {};
    return apiClient.get(`/achievements/student/${studentId}`, { params });
  },

  // Opportunities
  listOpportunities: (skip = 0, limit = 20, type = null) => {
    const params = { skip, limit };
    if (type) params.opportunity_type = type;
    return apiClient.get('/opportunities', { params });
  },
  getOpportunity: (id) => apiClient.get(`/opportunities/${id}`),
  saveOpportunity: (id) => apiClient.post(`/opportunities/${id}/save`),
  applyOpportunity: (id) => apiClient.post(`/opportunities/${id}/apply`),
  getSavedOpportunities: (studentId) => apiClient.get(`/opportunities/saved/student/${studentId}`),

  // Recommendations
  getRecommendations: (studentId, topK = 10, type = null) => {
    const params = { top_k: topK };
    if (type) params.opportunity_type = type;
    return apiClient.get(`/recommendations/${studentId}`, { params });
  },

  // Faculty
  getVerificationQueue: (skip = 0, limit = 50) => apiClient.get('/faculty/verification-queue', { params: { skip, limit } }),
  verifyAchievement: (id, status, remarks = '') => apiClient.post(`/faculty/verify/${id}`, { status, remarks }),
  talentSearch: (params) => apiClient.get('/faculty/talent-search', { params }),

  // Analytics
  getStudentAnalytics: (studentId) => apiClient.get(`/analytics/student/${studentId}`),
  getDepartmentAnalytics: (department) => apiClient.get(`/analytics/department/${encodeURIComponent(department)}`),
  getInstitutionalOverview: () => apiClient.get('/analytics/overview'),

  // Notifications
  getNotifications: (studentId, unreadOnly = false) => apiClient.get(`/notifications/${studentId}`, { params: { unread_only: unreadOnly } }),
  markNotificationRead: (id) => apiClient.patch(`/notifications/${id}/read`),

  // Reports
  getTranscriptUrl: (studentId) => `${API_BASE_URL}/reports/transcript/${studentId}`,
  getDeptReportUrl: (dept) => `${API_BASE_URL}/reports/department/${encodeURIComponent(dept)}`,
};

export default apiClient;
