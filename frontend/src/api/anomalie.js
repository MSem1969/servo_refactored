// =============================================================================
// ANOMALIE API
// =============================================================================

import api from './client';

export const anomalieApi = {
  getList: (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v));
    });
    return api.get(`/anomalie?${params}`).then(r => r.data);
  },

  getByOrdine: (id) => api.get(`/anomalie/ordine/${id}`).then(r => r.data),
  update: (id, data) => api.put(`/anomalie/${id}`, data).then(r => r.data),
  batchRisolvi: (ids, note) => api.post('/anomalie/batch/risolvi', { ids, note }).then(r => r.data),
  batchIgnora: (ids, note) => api.post('/anomalie/batch/ignora', { ids, note }).then(r => r.data),
  getTipi: () => api.get('/anomalie/tipi').then(r => r.data),
  getLivelli: () => api.get('/anomalie/livelli').then(r => r.data),
  getStati: () => api.get('/anomalie/stati').then(r => r.data),

  // Dettaglio anomalia con parent/child
  getDettaglio: (id) => api.get(`/anomalie/dettaglio/${id}`).then(r => r.data),
  modificaRiga: (id, data) => api.put(`/anomalie/dettaglio/${id}/riga`, data).then(r => r.data),
  risolviDettaglio: (id, note) => api.post(`/anomalie/dettaglio/${id}/risolvi`, { note }).then(r => r.data),
};
