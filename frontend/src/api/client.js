// =============================================================================
// SERV.O v10.1 - API CLIENT
// Base axios client con autenticazione JWT
// =============================================================================

import axios from 'axios';

// Configurazione
const isDev = import.meta.env.DEV;
const isCodespaces = window.location.hostname.includes('github.dev');
const isCloudflare = window.location.hostname.includes('trycloudflare.com');
const isRender = window.location.hostname.includes('onrender.com');

// URL Backend Cloudflare Tunnel
const CLOUDFLARE_BACKEND_URL = 'https://journalism-pleasant-jumping-difficulties.trycloudflare.com';

export function getApiBaseUrl() {
  // 1. Vite dev proxy (locale)
  if (isDev && !isCodespaces) return '';

  // 2. Cloudflare Tunnel
  if (isCloudflare) return CLOUDFLARE_BACKEND_URL;

  // 3. GitHub Codespaces
  if (isCodespaces) {
    const baseHost = window.location.hostname.replace(/-\d+\./, '-8000.');
    return `https://${baseHost}`;
  }

  // 4. Render (usa VITE_API_URL configurato nel build)
  if (isRender || import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL || '';
  }

  // 5. Fallback
  return 'http://localhost:8000';
}

export const API_URL = `${getApiBaseUrl()}/api/v1`;

// =============================================================================
// STORAGE KEYS
// =============================================================================
export const TOKEN_KEY = 'servo_token';
export const USER_KEY = 'servo_user';

// =============================================================================
// CLIENT AXIOS
// =============================================================================
const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

// =============================================================================
// REQUEST INTERCEPTOR
// =============================================================================
api.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (isDev) console.log(`API ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// =============================================================================
// RESPONSE INTERCEPTOR
// =============================================================================
api.interceptors.response.use(
  response => {
    if (isDev) console.log(`API ${response.status} ${response.config.url}`);
    return response;
  },
  error => {
    console.error('API Error:', error.response?.data || error.message);

    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    throw error;
  }
);

export default api;
