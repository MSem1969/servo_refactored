// =============================================================================
// LOOKUP API
// =============================================================================

import api from './client';

export const lookupApi = {
  test: (data) => api.post('/lookup/test', data).then(r => r.data),
  batch: (limit = 100) => api.post(`/lookup/batch?limit=${limit}`).then(r => r.data),

  manuale: (id, idFarmacia, idParafarmacia, minIdManuale = null) =>
    api.put(`/lookup/manuale/${id}`, {
      id_farmacia: idFarmacia,
      id_parafarmacia: idParafarmacia,
      min_id_manuale: minIdManuale
    }).then(r => r.data),

  getPending: (limit = 50) => api.get(`/lookup/pending?limit=${limit}`).then(r => r.data),

  searchFarmacie: (q, limit = 20) =>
    api.get(`/lookup/search/farmacie?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.data),

  searchParafarmacie: (q, limit = 20) =>
    api.get(`/lookup/search/parafarmacie?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.data),

  getStats: () => api.get('/lookup/stats').then(r => r.data),

  // Alternative lookup per P.IVA multipunto
  getAlternative: (idTestata) =>
    api.get(`/lookup/alternative/${idTestata}`).then(r => r.data),
};
