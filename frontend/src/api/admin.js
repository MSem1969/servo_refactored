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
};
