// =============================================================================
// ANOMALIE API - v8.2
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
  // v10.6: note è query param, non body
  risolviDettaglio: (id, options = {}) => {
    const params = new URLSearchParams();
    if (options.note) params.append('note', options.note);
    return api.post(`/anomalie/dettaglio/${id}/risolvi?${params}`).then(r => r.data);
  },

  // v8.2: Correzione AIC con propagazione
  correggiAic: (id, { codice_aic, livello_propagazione, operatore, note }) =>
    api.post(`/anomalie/dettaglio/${id}/correggi-aic`, {
      codice_aic,
      livello_propagazione,
      operatore,
      note
    }).then(r => r.data),

  // Contatori AIC per badge supervisione
  getContatoriAic: () => api.get('/anomalie/aic/contatori').then(r => r.data),

  // v10.5: Propagazione anomalie generica
  contaIdentiche: (id) => api.get(`/anomalie/dettaglio/${id}/conta-identiche`).then(r => r.data),

  getLivelliPermessi: (id, ruolo = 'operatore') =>
    api.get(`/anomalie/dettaglio/${id}/livelli-permessi?ruolo=${ruolo}`).then(r => r.data),

  risolviConPropagazione: (id, { livello_propagazione, operatore, ruolo, note }) =>
    api.post(`/anomalie/dettaglio/${id}/risolvi-propaga`, {
      livello_propagazione,
      operatore,
      ruolo,
      note
    }).then(r => r.data),

  // v10.6: Risoluzione LKP-A05 con deposito manuale
  risolviDeposito: (id, { deposito_riferimento, id_cliente, operatore, note }) =>
    api.post(`/anomalie/dettaglio/${id}/risolvi-deposito`, {
      deposito_riferimento,
      id_cliente,
      operatore,
      note
    }).then(r => r.data),
};
