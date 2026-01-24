// =============================================================================
// PERMESSI API
// =============================================================================

import api from './client';

export const permessiApi = {
  // Lista sezioni applicazione
  getSezioni: () => api.get('/permessi/sezioni').then(r => r.data),

  // Lista ruoli disponibili
  getRuoli: () => api.get('/permessi/ruoli').then(r => r.data),

  // Matrice completa permessi (solo admin)
  getMatrice: () => api.get('/permessi/matrice').then(r => r.data),

  // Permessi per ruolo specifico
  getPermessiRuolo: (ruolo) => api.get(`/permessi/ruolo/${ruolo}`).then(r => r.data),

  // Aggiorna singolo permesso
  updatePermesso: (ruolo, sezione, canView, canEdit) =>
    api.put(`/permessi/ruolo/${ruolo}/sezione/${sezione}`, {
      can_view: canView,
      can_edit: canEdit
    }).then(r => r.data),

  // Aggiorna tutti i permessi di un ruolo
  updatePermessiRuoloBulk: (ruolo, permessi) =>
    api.put(`/permessi/ruolo/${ruolo}/bulk`, permessi).then(r => r.data),

  // I miei permessi (utente corrente)
  getMyPermissions: () => api.get('/permessi/me').then(r => r.data),

  // Sezioni visibili per utente corrente
  getSezioniVisibili: () => api.get('/permessi/sezioni-visibili').then(r => r.data),
};
