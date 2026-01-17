// =============================================================================
// EMAIL CONFIG API
// =============================================================================

import api from './client';

export const emailApi = {
  // Configurazione completa (senza password, solo flag se configurate)
  getConfig: () => api.get('/email/config').then(r => r.data),

  // Salva configurazione (no password - quelle vanno in .env)
  saveConfig: (data) => api.put('/email/config', data).then(r => r.data),

  // Configurazione solo IMAP
  getImapConfig: () => api.get('/email/config/imap').then(r => r.data),

  // Configurazione solo SMTP
  getSmtpConfig: () => api.get('/email/config/smtp').then(r => r.data),

  // Test connessione IMAP
  testImap: () => api.post('/email/test/imap').then(r => r.data),

  // Test connessione SMTP (opzionalmente invia email test)
  testSmtp: (destinatario = null) =>
    api.post('/email/test/smtp', destinatario ? { destinatario } : {}).then(r => r.data),

  // Log email inviate
  getLog: (params = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v));
    });
    return api.get(`/email/log?${searchParams}`).then(r => r.data);
  },

  // Ritenta invio email fallita
  retryEmail: (logId) => api.post(`/email/log/${logId}/retry`).then(r => r.data),
};
