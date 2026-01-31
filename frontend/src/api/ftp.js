// =============================================================================
// FTP ENDPOINTS API - v11.6
// =============================================================================

import api from './client';

export const ftpApi = {
  // Lista tutti gli endpoint FTP
  getEndpoints: () => api.get('/ftp-endpoints').then(r => r.data),

  // Lista vendor e depositi disponibili
  getVendors: () => api.get('/ftp-endpoints/vendors').then(r => r.data),

  // Statistiche FTP
  getStats: () => api.get('/ftp-endpoints/stats').then(r => r.data),

  // Log FTP
  getLog: (limit = 100, endpointId = null) => {
    const params = { limit };
    if (endpointId) params.endpoint_id = endpointId;
    return api.get('/ftp-endpoints/log', { params }).then(r => r.data);
  },

  // Crea nuovo endpoint (NO 2FA)
  createEndpoint: (data) => api.post('/ftp-endpoints', data).then(r => r.data),

  // Richiedi OTP per operazione sensibile
  requestOtp: (endpointId, operation) =>
    api.post(`/ftp-endpoints/${endpointId}/request-otp?operation=${operation}`).then(r => r.data),

  // Visualizza password (RICHIEDE 2FA)
  viewPassword: (endpointId, otpCode) =>
    api.post(`/ftp-endpoints/${endpointId}/view-password`, { codice: otpCode }).then(r => r.data),

  // Aggiorna endpoint (RICHIEDE 2FA)
  updateEndpoint: (endpointId, data, otpCode) =>
    api.put(`/ftp-endpoints/${endpointId}?otp_code=${otpCode}`, data).then(r => r.data),

  // Elimina endpoint (RICHIEDE 2FA)
  deleteEndpoint: (endpointId, otpCode) =>
    api.delete(`/ftp-endpoints/${endpointId}?otp_code=${otpCode}`).then(r => r.data),

  // Toggle attivo/disattivo (NO 2FA)
  toggleEndpoint: (endpointId) =>
    api.patch(`/ftp-endpoints/${endpointId}/toggle`).then(r => r.data),

  // Test connessione FTP
  testConnection: (endpointId) =>
    api.post(`/ftp-endpoints/${endpointId}/test`).then(r => r.data),
};
