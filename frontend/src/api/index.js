// =============================================================================
// SERV.O v10.1 - API INDEX
// Exports all API modules
// =============================================================================

// Client and utilities
export { default as api, getApiBaseUrl, API_URL, TOKEN_KEY, USER_KEY } from './client';

// Auth
export { authApi } from './auth';

// Utenti
export { utentiApi } from './utenti';

// Dashboard
export { dashboardApi } from './dashboard';

// Upload
export { uploadApi } from './upload';

// Ordini
export { ordiniApi } from './ordini';

// Anagrafica
export { anagraficaApi } from './anagrafica';

// Tracciati
export { tracciatiApi } from './tracciati';

// Anomalie
export { anomalieApi } from './anomalie';

// Lookup
export { lookupApi } from './lookup';

// Supervisione
export { supervisioneApi } from './supervisione';

// Admin
export { adminApi } from './admin';

// Listini
export { listiniApi } from './listini';

// Mail Monitor
export { mailApi } from './mail';

// Produttivita
export { produttivitaApi } from './produttivita';

// Backup
export { backupApi } from './backup';

// Email Config
export { emailApi } from './email';

// CRM
export { crmApi } from './crm';

// Report
export { reportApi } from './report';

// Permessi
export { permessiApi } from './permessi';

// FTP Endpoints (v11.6)
export { ftpApi } from './ftp';

// Default export: axios client
import api from './client';
export default api;
