// =============================================================================
// REPORT API
// =============================================================================
// v11.0: TIER 3.2 - Usa buildQueryParams centralizzato
// =============================================================================

import api from './client';
import { buildQueryParams } from '../hooks/utils';

export const reportApi = {
  // Dati report consolidato con filtri
  getData: (filters = {}) => {
    const params = buildQueryParams(filters);
    return api.get(`/report/export/data?${params}`).then(r => r.data);
  },

  // URL download Excel (blob response)
  downloadExcel: (filters = {}) => {
    const params = buildQueryParams(filters);
    return api.get(`/report/export/excel?${params}`, {
      responseType: 'blob'
    }).then(r => {
      // Crea URL blob e triggera download
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const link = document.createElement('a');
      link.href = url;
      // Estrai nome file dall'header o usa default
      const contentDisposition = r.headers['content-disposition'];
      let filename = 'report_ordini.xlsx';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) filename = match[1].replace(/['"]/g, '');
      }
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      return { success: true, filename };
    });
  },

  // Lista vendor disponibili (con filtri a cascata)
  getVendors: (cascadeFilters = {}) => {
    const params = buildQueryParams(cascadeFilters);
    return api.get(`/report/filters/vendors?${params}`).then(r => r.data);
  },

  // Lista depositi disponibili (con filtri a cascata)
  getDepositi: (cascadeFilters = {}) => {
    const params = buildQueryParams(cascadeFilters);
    return api.get(`/report/filters/depositi?${params}`).then(r => r.data);
  },

  // Lista stati ordine disponibili (con filtri a cascata)
  getStati: (cascadeFilters = {}) => {
    const params = buildQueryParams(cascadeFilters);
    return api.get(`/report/filters/stati?${params}`).then(r => r.data);
  },

  // Ricerca clienti (con filtri a cascata)
  searchClienti: (q = null, limit = 50, cascadeFilters = {}) => {
    const params = buildQueryParams({ ...cascadeFilters, q, limit });
    return api.get(`/report/filters/clienti?${params}`).then(r => r.data);
  },

  // Ricerca prodotti per AIC o descrizione (con filtri a cascata)
  searchProdotti: (q = null, limit = 100, cascadeFilters = {}) => {
    const params = buildQueryParams({ ...cascadeFilters, q, limit });
    return api.get(`/report/filters/prodotti?${params}`).then(r => r.data);
  },
};
