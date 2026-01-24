// =============================================================================
// DASHBOARD API
// =============================================================================

import api from './client';

export const dashboardApi = {
  getStats: () => api.get('/dashboard').then(r => r.data),
  getSummary: () => api.get('/dashboard/summary').then(r => r.data),
  getOrdiniRecenti: (limit = 10) => api.get(`/dashboard/ordini-recenti?limit=${limit}`).then(r => r.data),
  getAnomalieCritiche: (limit = 10) => api.get(`/dashboard/anomalie-critiche?limit=${limit}`).then(r => r.data),
  getVendorStats: () => api.get('/dashboard/vendor-stats').then(r => r.data),
  getAnagraficaStats: () => api.get('/dashboard/anagrafica-stats').then(r => r.data),
};
