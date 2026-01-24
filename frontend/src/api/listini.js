// =============================================================================
// LISTINI API
// =============================================================================

import api from './client';

export const listiniApi = {
  // Statistiche listini caricati
  getStats: () => api.get('/listini/stats').then(r => r.data),

  // Import listino CSV per vendor
  importListino: (file, vendor, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/listini/import?vendor=${encodeURIComponent(vendor)}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  // Elimina listino di un vendor
  deleteListino: (vendor) => api.delete(`/listini/${encodeURIComponent(vendor)}`).then(r => r.data),
};
