// =============================================================================
// UTENTI API
// =============================================================================
// v11.0: TIER 3.2 - Usa buildQueryParams centralizzato
// =============================================================================

import api from './client';
import { buildQueryParams } from '../hooks/utils';

export const utentiApi = {
  getList: (params = {}) => {
    const searchParams = buildQueryParams(params);
    return api.get(`/utenti?${searchParams}`).then(r => r.data);
  },

  getDetail: (id) => api.get(`/utenti/${id}`).then(r => r.data),

  create: (data) => api.post('/utenti', data).then(r => r.data),

  update: (id, data) => api.patch(`/utenti/${id}`, data).then(r => r.data),

  changePassword: (id, data) => api.post(`/utenti/${id}/cambio-password`, data),

  disable: (id, motivo = null) => api.post(`/utenti/${id}/disabilita`, { motivo }).then(r => r.data),

  enable: (id) => api.post(`/utenti/${id}/riabilita`).then(r => r.data),

  getLogs: (id, params = {}) => {
    const searchParams = buildQueryParams(params);
    return api.get(`/utenti/${id}/logs?${searchParams}`).then(r => r.data);
  },

  updateProfilo: (data) => api.patch('/utenti/me/profilo', data).then(r => r.data),
};
