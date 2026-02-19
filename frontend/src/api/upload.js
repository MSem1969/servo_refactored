// =============================================================================
// UPLOAD API
// =============================================================================

import api from './client';

export const uploadApi = {
  uploadPdf: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  uploadMultiple: (files, onProgress) => {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    return api.post('/upload/multiple', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  getRecent: (limit = 20) => api.get(`/upload/recent?limit=${limit}`).then(r => r.data),
  getStats: () => api.get('/upload/stats').then(r => r.data),
  getErrors: (limit = 50) => api.get(`/upload/errors?limit=${limit}`).then(r => r.data),
  getVendors: () => api.get('/upload/vendors').then(r => r.data),
};
