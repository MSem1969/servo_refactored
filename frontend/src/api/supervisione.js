// =============================================================================
// SUPERVISIONE API
// =============================================================================

import api from './client';

export const supervisioneApi = {
  // === SUPERVISIONI PENDING ===
  getPending: () => api.get('/supervisione/pending').then(r => r.data),
  getPendingCount: () => api.get('/supervisione/pending/count').then(r => r.data),

  // === DETTAGLIO ===
  getDetail: (id) => api.get(`/supervisione/${id}`).then(r => r.data),
  getByOrdine: (idTestata) => api.get(`/supervisione/ordine/${idTestata}`).then(r => r.data),

  // === DECISIONI BASE ===
  approva: (id, operatore, note = null) =>
    api.post(`/supervisione/${id}/approva`, { operatore, note }).then(r => r.data),
  rifiuta: (id, operatore, note) =>
    api.post(`/supervisione/${id}/rifiuta`, { operatore, note }).then(r => r.data),
  modifica: (id, operatore, modifiche, note = null) =>
    api.post(`/supervisione/${id}/modifica`, { operatore, modifiche, note }).then(r => r.data),

  // === AZIONI CON RITORNO A ORDINE ===
  approvaETorna: (id, operatore, note = null) =>
    api.post(`/supervisione/${id}/completa-e-torna`, { operatore, note }).then(r => r.data),
  modificaETorna: (id, operatore, modifiche, note = null) =>
    api.post(`/supervisione/${id}/modifica-e-torna`, { operatore, modifiche, note }).then(r => r.data),
  lasciaSospeso: (id, operatore) =>
    api.post(`/supervisione/${id}/lascia-sospeso?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // === CRITERI ML ===
  getCriteriOrdinari: () => api.get('/supervisione/criteri/ordinari').then(r => r.data),
  getCriteriTutti: () => api.get('/supervisione/criteri/tutti').then(r => r.data),
  getCriteriStats: () => api.get('/supervisione/criteri/stats').then(r => r.data),
  getPattern: (signature) => api.get(`/supervisione/criteri/${signature}`).then(r => r.data),
  resetPattern: (signature, operatore) =>
    api.post(`/supervisione/criteri/${signature}/reset?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  promuoviPattern: (signature, operatore) =>
    api.post(`/supervisione/criteri/${signature}/promuovi?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // === STORICO ===
  getStorico: (limit = 50) => api.get(`/supervisione/criteri/storico/applicazioni?limit=${limit}`).then(r => r.data),

  // === SUPERVISIONE LISTINO ===
  getListinoDetail: (id) => api.get(`/supervisione/listino/${id}`).then(r => r.data),
  correggiListino: (id, data) => api.post(`/supervisione/listino/${id}/correggi`, data).then(r => r.data),
  archiviaListino: (id, data) => api.post(`/supervisione/listino/${id}/archivia`, data).then(r => r.data),
  getListinoPattern: (codiceAic) => api.get(`/supervisione/listino/pattern/${codiceAic}`).then(r => r.data),

  // === SUPERVISIONE RAGGRUPPATA PER PATTERN ===
  getPendingGrouped: () => api.get('/supervisione/pending/grouped').then(r => r.data),
  approvaBulk: (patternSignature, operatore, note = null) =>
    api.post(`/supervisione/pattern/${encodeURIComponent(patternSignature)}/approva-bulk`, { operatore, note }).then(r => r.data),
  rifiutaBulk: (patternSignature, operatore, note) =>
    api.post(`/supervisione/pattern/${encodeURIComponent(patternSignature)}/rifiuta-bulk`, { operatore, note }).then(r => r.data),

  // === SUPERVISIONE LOOKUP ===
  getLookupDetail: (id) => api.get(`/supervisione/lookup/${id}`).then(r => r.data),
  risolviLookup: (id, data) => api.post(`/supervisione/lookup/${id}/risolvi`, data).then(r => r.data),
  rifiutaLookup: (id, operatore, note) =>
    api.post(`/supervisione/lookup/${id}/rifiuta`, { operatore, note }).then(r => r.data),

  // === SUPERVISIONE PREZZO ===
  riapplicaListinoBulk: (operatore) =>
    api.post(`/supervisione/prezzo/riapplica-listino?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  riapplicaListinoLstBulk: (operatore) =>
    api.post(`/supervisione/listino/riapplica-listino?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // === SUPERVISIONE AIC ===
  getAicPending: () => api.get('/supervisione/aic/pending').then(r => r.data),
  getAicDetail: (id) => api.get(`/supervisione/aic/${id}`).then(r => r.data),
  risolviAic: (id, operatore, codiceAic, livelloPropagazione = 'GLOBALE', note = null) =>
    api.post(`/supervisione/aic/${id}/risolvi`, {
      operatore,
      codice_aic: codiceAic,
      livello_propagazione: livelloPropagazione,
      note
    }).then(r => r.data),
  rifiutaAic: (id, operatore, note) =>
    api.post(`/supervisione/aic/${id}/rifiuta`, { operatore, note }).then(r => r.data),
  searchAic: (descrizione, vendor = null) => {
    const params = new URLSearchParams({ descrizione });
    if (vendor) params.append('vendor', vendor);
    return api.get(`/supervisione/aic/search-aic?${params}`).then(r => r.data);
  },
  getAicStats: () => api.get('/supervisione/aic/stats').then(r => r.data),
  approvaBulkAic: (patternSignature, operatore, codiceAic, note = null) =>
    api.post(`/supervisione/aic/pattern/${encodeURIComponent(patternSignature)}/approva-bulk`, {
      operatore,
      codice_aic: codiceAic,
      note
    }).then(r => r.data),

  // === CORREZIONE ERRORI AIC (v8.2) ===
  correggiErroreAic: (aicErrato, aicCorretto, operatore, note = null) =>
    api.post('/supervisione/aic/correggi-errore', {
      aic_errato: aicErrato,
      aic_corretto: aicCorretto,
      operatore,
      note
    }).then(r => r.data),

  getStoricoModificheAic: (codiceAic = null, limit = 50) => {
    const params = new URLSearchParams();
    if (codiceAic) params.append('codice_aic', codiceAic);
    params.append('limit', limit);
    return api.get(`/supervisione/aic/storico-modifiche?${params}`).then(r => r.data);
  },
};
