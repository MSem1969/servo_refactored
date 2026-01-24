// =============================================================================
// AUTH API
// =============================================================================

import api, { TOKEN_KEY, USER_KEY } from './client';

export const authApi = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }).then(r => {
      const { access_token, user } = r.data;
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return r.data;
    }),

  logout: () =>
    api.post('/auth/logout')
      .catch(() => {})
      .finally(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }),

  getMe: () => api.get('/auth/me').then(r => r.data),

  getMyPermissions: () => api.get('/auth/me/permissions').then(r => r.data),

  getMySessions: () => api.get('/auth/me/sessions').then(r => r.data),

  revokeSession: (id) => api.delete(`/auth/me/sessions/${id}`),

  revokeOtherSessions: () => api.post('/auth/me/sessions/revoke-others'),

  // Password recovery (v8.2)
  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }).then(r => r.data),

  resetPassword: (token, nuova_password) =>
    api.post('/auth/reset-password', { token, nuova_password }).then(r => r.data),

  isAuthenticated: () => !!localStorage.getItem(TOKEN_KEY),

  getStoredUser: () => {
    const userJson = localStorage.getItem(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  },

  getToken: () => localStorage.getItem(TOKEN_KEY),
};
