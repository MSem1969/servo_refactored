// =============================================================================
// CRM API
// =============================================================================

import api from './client';

export const crmApi = {
  // === TICKETS ===

  // Lista ticket (admin vede tutti, user solo propri)
  getTickets: (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v));
    });
    return api.get(`/crm/tickets?${params}`).then(r => r.data);
  },

  // Crea nuovo ticket
  createTicket: (data) => api.post('/crm/tickets', data).then(r => r.data),

  // Dettaglio ticket con messaggi
  getTicket: (id) => api.get(`/crm/tickets/${id}`).then(r => r.data),

  // Aggiorna stato ticket (solo admin)
  updateStatus: (id, stato) =>
    api.patch(`/crm/tickets/${id}/stato`, { stato }).then(r => r.data),

  // Aggiorna altri campi ticket
  updateTicket: (id, data) =>
    api.patch(`/crm/tickets/${id}`, data).then(r => r.data),

  // === MESSAGGI ===

  // Lista messaggi di un ticket
  getMessages: (ticketId) =>
    api.get(`/crm/tickets/${ticketId}/messaggi`).then(r => r.data),

  // Aggiungi messaggio a ticket
  addMessage: (ticketId, contenuto) =>
    api.post(`/crm/tickets/${ticketId}/messaggi`, { contenuto }).then(r => r.data),

  // === STATISTICHE ===

  // Statistiche ticket (admin globali, user propri)
  getStats: () => api.get('/crm/stats').then(r => r.data),

  // Costanti per UI (stati, categorie, priorita)
  getConstants: () => api.get('/crm/constants').then(r => r.data),

  // === ALLEGATI ===

  // Upload allegato
  uploadAttachment: (ticketId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/crm/tickets/${ticketId}/allegati`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data);
  },

  // Lista allegati ticket
  getAttachments: (ticketId) =>
    api.get(`/crm/tickets/${ticketId}/allegati`).then(r => r.data),

  // Download allegato (ritorna URL)
  getAttachmentUrl: (allegatoId) =>
    `${api.defaults.baseURL}/crm/allegati/${allegatoId}/download`,

  // Elimina allegato
  deleteAttachment: (allegatoId) =>
    api.delete(`/crm/allegati/${allegatoId}`).then(r => r.data),
};
