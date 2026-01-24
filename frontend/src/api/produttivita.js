// =============================================================================
// PRODUTTIVITA API
// =============================================================================

import api from './client';

export const produttivitaApi = {
  // Heartbeat per tracking tempo sezione
  heartbeat: (sezione) => api.post('/produttivita/heartbeat', { sezione }).then(r => r.data),

  // Produttivita sessione corrente
  getSessione: () => api.get('/produttivita/sessione').then(r => r.data),

  // Produttivita giornaliera
  getGiorno: (data) => api.get(`/produttivita/giorno/${data}`).then(r => r.data),

  // Ultime task di un operatore
  getUltimeTask: (idOperatore = null, limit = 10) => {
    const params = { limit };
    if (idOperatore) params.id_operatore = idOperatore;
    return api.get('/produttivita/ultime-task', { params }).then(r => r.data);
  },
};
