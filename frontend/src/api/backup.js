// =============================================================================
// BACKUP API
// =============================================================================
// v11.0: TIER 3.2 - Usa buildQueryParams centralizzato
// =============================================================================

import api from './client';
import { buildQueryParams } from '../hooks/utils';

export const backupApi = {
  // === MODULI ===

  // Lista moduli backup disponibili
  getModules: () => api.get('/backup/modules').then(r => r.data),

  // Dettaglio singolo modulo
  getModule: (name) => api.get(`/backup/modules/${name}`).then(r => r.data),

  // Stato corrente modulo (health check)
  getModuleStatus: (name) => api.get(`/backup/modules/${name}/status`).then(r => r.data),

  // Configura modulo (richiede admin)
  configureModule: (name, config) =>
    api.post(`/backup/modules/${name}/configure`, { config }).then(r => r.data),

  // Abilita modulo (richiede admin)
  enableModule: (name) => api.post(`/backup/modules/${name}/enable`).then(r => r.data),

  // Disabilita modulo (richiede admin)
  disableModule: (name) => api.post(`/backup/modules/${name}/disable`).then(r => r.data),

  // Testa modulo (richiede admin)
  testModule: (name) => api.post(`/backup/modules/${name}/test`).then(r => r.data),

  // === ESECUZIONE ===

  // Esegue backup per modulo (richiede admin)
  executeBackup: (name, triggeredBy = 'manual') =>
    api.post(`/backup/modules/${name}/execute`, { triggered_by: triggeredBy }).then(r => r.data),

  // Cleanup backup vecchi per modulo (richiede admin)
  cleanupModule: (name, retentionDays = null) =>
    api.post(`/backup/modules/${name}/cleanup`, { retention_days: retentionDays }).then(r => r.data),

  // === DASHBOARD E STORICO ===

  // Dashboard statistiche backup
  getDashboard: () => api.get('/backup/dashboard').then(r => r.data),

  // Storico backup eseguiti
  getHistory: (params = {}) => {
    const searchParams = buildQueryParams(params);
    return api.get(`/backup/history?${searchParams}`).then(r => r.data);
  },

  // === STORAGE ===

  // Lista storage locations
  getStorageLocations: () => api.get('/backup/storage').then(r => r.data),

  // Aggiungi storage location (richiede admin)
  addStorageLocation: (data) => api.post('/backup/storage', data).then(r => r.data),
};
