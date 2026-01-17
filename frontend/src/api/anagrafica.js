// =============================================================================
// ANAGRAFICA API
// =============================================================================

import api from './client';

export const anagraficaApi = {
  importFarmacie: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/anagrafica/farmacie/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  importParafarmacie: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/anagrafica/parafarmacie/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  importClienti: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/anagrafica/clienti/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data);
  },

  getStats: () => api.get('/anagrafica/stats').then(r => r.data),

  search: (q, tipo = 'all', limit = 20) =>
    api.get(`/anagrafica/search?q=${encodeURIComponent(q)}&tipo=${tipo}&limit=${limit}`).then(r => r.data),

  getFarmacia: (id) => api.get(`/anagrafica/farmacie/${id}`).then(r => r.data),

  getFarmacieByPiva: (piva) => api.get(`/anagrafica/farmacie/piva/${piva}`).then(r => r.data),

  clearFarmacie: () => api.delete('/anagrafica/farmacie?confirm=true').then(r => r.data),

  clearParafarmacie: () => api.delete('/anagrafica/parafarmacie?confirm=true').then(r => r.data),

  clearClienti: () => api.delete('/anagrafica/clienti?confirm=true').then(r => r.data),
};
