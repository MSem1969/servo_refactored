// =============================================================================
// ADMIN API
// =============================================================================

import api from './client';

export const adminApi = {
  // Crea backup database
  backup: () => api.post('/admin/backup').then(r => r.data),

  // Elimina tutti gli ordini (richiede conferma)
  clearOrdini: () => api.delete('/admin/ordini/all?confirm=CONFERMA').then(r => r.data),

  // Reset completo sistema (richiede conferma)
  resetSistema: () => api.post('/admin/reset?confirm=RESET_COMPLETO').then(r => r.data),

  // Recupera impostazioni
  getSettings: () => api.get('/admin/settings').then(r => r.data),

  // Salva impostazioni
  saveSettings: (settings) => api.put('/admin/settings', settings).then(r => r.data),

  // =========================================================================
  // SINCRONIZZAZIONE ANAGRAFICA MINISTERO (v8.2)
  // =========================================================================

  // Stato sincronizzazione (farmacie + parafarmacie)
  getSyncStatus: () => api.get('/admin/sync/status').then(r => r.data),

  // Sync solo farmacie
  syncFarmacie: (force = false) =>
    api.post(`/admin/sync/farmacie?force=${force}`).then(r => r.data),

  // Sync solo parafarmacie
  syncParafarmacie: (force = false) =>
    api.post(`/admin/sync/parafarmacie?force=${force}`).then(r => r.data),

  // Sync entrambe
  syncAll: (force = false) =>
    api.post(`/admin/sync/all?force=${force}`).then(r => r.data),

  // Lista subentri recenti
  getSubentri: (days = 30) =>
    api.get(`/admin/sync/subentri?days=${days}`).then(r => r.data),
};
