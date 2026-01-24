// =============================================================================
// MAIL MONITOR API
// =============================================================================
// v11.0: TIER 3.2 - Usa buildQueryParams centralizzato
// =============================================================================

import api from './client';
import { buildQueryParams } from '../hooks/utils';

export const mailApi = {
  // Stato e configurazione Mail Monitor
  getStatus: () => api.get('/mail/status').then(r => r.data),

  // Avvia sincronizzazione manuale
  sync: () => api.post('/mail/sync').then(r => r.data),

  // Lista email scaricate (con paginazione e filtri)
  getEmails: (params = {}) => {
    const searchParams = buildQueryParams(params);
    return api.get(`/mail/emails?${searchParams}`).then(r => r.data);
  },

  // Dettaglio singola email
  getEmail: (id) => api.get(`/mail/emails/${id}`).then(r => r.data),

  // Ritenta elaborazione email in errore
  retryEmail: (id) => api.post(`/mail/emails/${id}/retry`).then(r => r.data),

  // Statistiche dettagliate
  getStats: () => api.get('/mail/stats').then(r => r.data),
};
