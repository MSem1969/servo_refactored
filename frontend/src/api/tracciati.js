// =============================================================================
// TRACCIATI API
// =============================================================================

import api, { API_URL } from './client';

export const tracciatiApi = {
  genera: (ordiniIds) => api.post('/tracciati/genera', ordiniIds ? { ordini_ids: ordiniIds } : {}).then(r => r.data),
  generaSingolo: (id) => api.post(`/tracciati/genera/${id}`).then(r => r.data),
  getPreview: (id) => api.get(`/tracciati/preview/${id}`).then(r => r.data),
  getPronti: () => api.get('/tracciati/pronti').then(r => r.data),
  getStorico: (limit = 20) => api.get(`/tracciati/storico?limit=${limit}`).then(r => r.data),
  getFiles: () => api.get('/tracciati/files').then(r => r.data),
  deleteFiles: () => api.delete('/tracciati/files?confirm=true').then(r => r.data),
  getDownloadUrl: (filename) => `${API_URL}/tracciati/download/${filename}`,
  updateDifarm: (idTestata, difarm) => api.patch(`/tracciati/${idTestata}/difarm`, { difarm }).then(r => r.data),

  // Riemissione tracciato (admin only)
  getRaw: (idEsportazione) => api.get(`/tracciati/${idEsportazione}/raw`).then(r => r.data),
  riemetti: (idEsportazione, payload) => api.post(`/tracciati/${idEsportazione}/riemetti`, payload).then(r => r.data),
  ritrasmetti: (idEsportazione) => api.post(`/tracciati/${idEsportazione}/ritrasmetti`).then(r => r.data),
};
